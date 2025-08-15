from rest_framework import status
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from dj_rest_auth.serializers import UserDetailsSerializer
from returns.result import Success, Failure
from startup.shared.repository import NotFoundError
from startup.accounts.features import GetAccountProfile
from startup.accounts.repository import DjUserAccountsRepository


class AccountProfileViewSet(ViewSet):
    """
    Viewset to manage the account profile for the authenticated user.
    """
    
    allowed_methods = ['GET']
    permission_classes = [IsAuthenticated]
    serializer_class = UserDetailsSerializer
    
    user_accounts_repository = DjUserAccountsRepository()
    get_account_profile = GetAccountProfile(user_accounts_repository)
    
    def retrieve(self, request, *args, **kwargs):
        
        match self.get_account_profile.execute(request.user.id):
            
            case Success(user):
                serializer = UserDetailsSerializer(user)
                return Response(status=status.HTTP_200_OK, data=serializer.data)
            
            case Failure(NotFoundError()):
                return Response(status=status.HTTP_404_NOT_FOUND)
