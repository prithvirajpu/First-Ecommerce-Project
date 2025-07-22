from user_app.models import Wallet, WalletTransaction

def update_wallet(user, amount, txn_type, description="", order=None):
    wallet, created = Wallet.objects.get_or_create(user=user)

    if txn_type == 'CREDIT':
        wallet.balance += amount
    elif txn_type == 'DEBIT':
        if wallet.balance < amount:
            raise ValueError("Insufficient wallet balance")
        wallet.balance -= amount
    wallet.save()

    WalletTransaction.objects.create(
        wallet=wallet,
        amount=amount,
        transaction_type=txn_type,
        description=description,
        order=order
    )
