import uuid
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timezone

from api.db.database import get_db
from api.v1.models.wallet import Wallet
from api.v1.models.transaction import Transaction, TransactionType, TransactionDirection, TransactionStatus
from api.v1.models.webhook_log import WebhookLog
from api.utils.deps import get_authenticated_user, require_permission
from api.utils.paystack import initialize_transaction, verify_transaction, verify_paystack_signature
from api.utils.responses import success_response, fail_response

router = APIRouter(prefix="/wallet", tags=["Wallet"])


class DepositRequest(BaseModel):
    amount: int  # Amount in kobo


class TransferRequest(BaseModel):
    wallet_number: str
    amount: int  # Amount in kobo


@router.post("/deposit")
async def deposit_to_wallet(
    request: DepositRequest,
    user = Depends(require_permission("deposit")),
    db: Session = Depends(get_db)
):
    """Initialize Paystack deposit transaction"""
    
    if request.amount < 100:  # Minimum 1 naira (100 kobo)
        raise HTTPException(status_code=400, detail="Minimum deposit is 100 kobo (1 NGN)")
    
    # Get user's wallet
    wallet = Wallet.fetch_one(db, user_id=user.id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    # Generate unique reference
    reference = f"dep_{uuid.uuid4().hex[:16]}"
    
    # Create pending transaction
    transaction = Transaction(
        reference=reference,
        wallet_id=wallet.id,
        user_id=user.id,
        type=TransactionType.DEPOSIT,
        direction=TransactionDirection.CREDIT,
        amount=request.amount,
        status=TransactionStatus.PENDING
    )
    transaction.insert(db)
    
    # Initialize Paystack transaction
    try:
        paystack_response = await initialize_transaction(
            email=user.email,
            amount=request.amount,
            reference=reference
        )
        
        if not paystack_response.get("status"):
            raise HTTPException(status_code=500, detail="Failed to initialize payment")
        
        data = paystack_response.get("data", {})
        
        return success_response(
            status_code=200,
            message="Deposit initialized",
            data={
                "reference": reference,
                "authorization_url": data.get("authorization_url")
            }
        )
    
    except Exception as e:
        # Mark transaction as failed
        transaction.status = TransactionStatus.FAILED
        transaction.update(db)
        raise HTTPException(status_code=500, detail=f"Payment initialization failed: {str(e)}")


@router.post("/paystack/webhook")
async def paystack_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle Paystack webhook events"""
    
    # Get signature from header
    signature = request.headers.get("x-paystack-signature")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature")
    
    # Get raw body
    body = await request.body()
    
    # Verify signature
    if not verify_paystack_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse payload
    payload = await request.json()
    
    # Log webhook
    webhook_log = WebhookLog(
        provider="paystack",
        payload=payload,
        headers=dict(request.headers),
        processed=False
    )
    webhook_log.insert(db, commit=False)
    
    # Process event
    event = payload.get("event")
    data = payload.get("data", {})
    
    if event == "charge.success":
        reference = data.get("reference")
        amount = data.get("amount")  # Amount in kobo
        status = data.get("status")
        
        if not reference:
            webhook_log.processed = True
            db.commit()
            return {"status": True}
        
        # Find transaction
        transaction = Transaction.fetch_one(db, reference=reference)
        
        if not transaction:
            webhook_log.processed = True
            db.commit()
            return {"status": True}
        
        # Idempotency check - already processed
        if transaction.status == TransactionStatus.SUCCESS:
            webhook_log.processed = True
            db.commit()
            return {"status": True}
        
        # Update transaction
        if status == "success":
            transaction.status = TransactionStatus.SUCCESS
            transaction.extra = data
            
            # Credit wallet
            wallet = Wallet.fetch_one(db, id=transaction.wallet_id)
            if wallet:
                wallet.credit(amount)
                wallet.update(db, commit=False)
            
            transaction.update(db, commit=False)
        
        webhook_log.processed = True
        db.commit()
    
    return {"status": True}


@router.get("/deposit/{reference}/status")
async def check_deposit_status(
    reference: str,
    user = Depends(require_permission("read")),
    db: Session = Depends(get_db)
):
    """Check deposit transaction status (does not credit wallet)"""
    
    transaction = Transaction.fetch_one(db, reference=reference, user_id=user.id)
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Optionally verify with Paystack
    try:
        paystack_data = await verify_transaction(reference)
        paystack_status = paystack_data.get("data", {}).get("status")
        
        return success_response(
            status_code=200,
            message="Transaction status retrieved",
            data={
                "reference": reference,
                "status": transaction.status.value,
                "amount": transaction.amount,
                "paystack_status": paystack_status
            }
        )
    except Exception:
        return success_response(
            status_code=200,
            message="Transaction status retrieved",
            data={
                "reference": reference,
                "status": transaction.status.value,
                "amount": transaction.amount
            }
        )


@router.get("/balance")
async def get_wallet_balance(
    user = Depends(require_permission("read")),
    db: Session = Depends(get_db)
):
    """Get wallet balance"""
    
    wallet = Wallet.fetch_one(db, user_id=user.id)
    
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    return success_response(
        status_code=200,
        message="Balance retrieved",
        data={
            "balance": wallet.balance,
            "currency": wallet.currency
        }
    )


@router.post("/transfer")
async def transfer_funds(
    request: TransferRequest,
    user = Depends(require_permission("transfer")),
    db: Session = Depends(get_db)
):
    """Transfer funds to another wallet"""
    
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")
    
    # Get sender wallet
    sender_wallet = Wallet.fetch_one(db, user_id=user.id)
    if not sender_wallet:
        raise HTTPException(status_code=404, detail="Sender wallet not found")
    
    # Check sufficient balance
    if sender_wallet.balance < request.amount:
        return fail_response(
            status_code=400,
            message="Insufficient balance",
            context={
                "balance": sender_wallet.balance,
                "required": request.amount
            }
        )
    
    # Get recipient wallet
    recipient_wallet = Wallet.fetch_one(db, wallet_number=request.wallet_number)
    if not recipient_wallet:
        raise HTTPException(status_code=404, detail="Recipient wallet not found")
    
    if recipient_wallet.id == sender_wallet.id:
        raise HTTPException(status_code=400, detail="Cannot transfer to self")
    
    # Generate unique reference
    reference = f"txf_{uuid.uuid4().hex[:16]}"
    
    # Create debit transaction for sender
    debit_tx = Transaction(
        reference=f"{reference}_debit",
        wallet_id=sender_wallet.id,
        user_id=user.id,
        type=TransactionType.TRANSFER,
        direction=TransactionDirection.DEBIT,
        amount=request.amount,
        status=TransactionStatus.SUCCESS,
        extra={"recipient_wallet": request.wallet_number}
    )
    
    # Create credit transaction for recipient
    credit_tx = Transaction(
        reference=f"{reference}_credit",
        wallet_id=recipient_wallet.id,
        user_id=recipient_wallet.user_id,
        type=TransactionType.TRANSFER,
        direction=TransactionDirection.CREDIT,
        amount=request.amount,
        status=TransactionStatus.SUCCESS,
        extra={"sender_wallet": sender_wallet.wallet_number}
    )
    
    # Link transactions
    debit_tx.insert(db, commit=False)
    credit_tx.related_tx_id = debit_tx.id
    debit_tx.related_tx_id = credit_tx.id
    
    # Update balances
    sender_wallet.debit(request.amount)
    recipient_wallet.credit(request.amount)
    
    # Commit all changes atomically
    credit_tx.insert(db, commit=False)
    sender_wallet.update(db, commit=False)
    recipient_wallet.update(db, commit=False)
    db.commit()
    
    return success_response(
        status_code=200,
        message="Transfer completed",
        data={
            "reference": reference,
            "amount": request.amount,
            "recipient": request.wallet_number
        }
    )


@router.get("/transactions")
async def get_transaction_history(
    user = Depends(require_permission("read")),
    db: Session = Depends(get_db)
):
    """Get transaction history"""
    
    wallet = Wallet.fetch_one(db, user_id=user.id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    transactions = Transaction.fetch_all(db, wallet_id=wallet.id)
    
    transaction_list = [
        {
            "id": str(tx.id),
            "type": tx.type.value,
            "direction": tx.direction.value,
            "amount": tx.amount,
            "status": tx.status.value,
            "reference": tx.reference,
            "created_at": tx.created_at.isoformat(),
            "extra": tx.extra
        }
        for tx in transactions
    ]
    
    return success_response(
        status_code=200,
        message="Transactions retrieved",
        data={"transactions": transaction_list}
    )