from django.contrib.auth import get_user_model
from startup.shared.filters import Criteria
from startup.shared.repository import DjangoRepository, Repository


UserModel = get_user_model()


class UserAccountCriteria(Criteria):
    """ Users search filters """
    pass


class UserAccountsRepository(Repository[UserModel, UserAccountCriteria]):
    pass


class DjUserAccountsRepository(DjangoRepository, UserAccountsRepository):
    model = UserModel

