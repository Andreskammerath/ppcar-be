from returns.result import Result
from startup.shared.repository import NotFoundError
from startup.accounts.models import User
from startup.accounts.repository import UserAccountsRepository


class GetAccountProfile:
    """
    Returns the account profile for a given user id.
    """

    def __init__(self, user_accounts_repository: UserAccountsRepository):
        self.user_accounts_repository = user_accounts_repository

    def execute(self, user_id: str) -> Result[User, NotFoundError]:
        return self.user_accounts_repository.get_by_id(user_id)
