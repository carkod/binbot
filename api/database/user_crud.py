from fastapi import HTTPException
from sqlmodel import Session, desc, select
from database.models.user_table import UserTable
from database.utils import independent_session
from collections.abc import Sequence
from tools.exceptions import BinbotErrors
from passlib.hash import pbkdf2_sha256
from user.models.user import LoginRequest, UserDetails
from user.services.auth import encode_access_token


class UserTableCrud:
    """
    CRUD and database operations for the SQL API DB
    bot_table table.

    Use for lower level APIs that require a session
    e.g.
    client-side -> receive json -> bots.routes -> BotModelCrud
    """

    def __init__(
        self,
        # Some instances of AutotradeSettingsController are used outside of the FastAPI context
        # this is designed this way for reusability
        session: Session | None = None,
    ):
        if session is None:
            session = independent_session()
        self.session = session

    def hash_password(self, password):
        password_bytes = password.encode("utf-8")
        hash_object = pbkdf2_sha256.encrypt(password_bytes, rounds=20000, salt_size=16)
        return hash_object.hexdigest()

    def get(self, limit: int = 200, offset: int = 0) -> Sequence[UserTable]:
        """
        Get all bots in the db except archived
        Args:
        - status: Status enum
        - start_date and end_date are timestamps in milliseconds
        - no_cooldown: bool - filter out bots that are in cooldown
        - limit and offset for pagination
        """
        statement = (
            select(UserTable)
            .order_by(desc(UserTable.created_at))
            .limit(limit)
            .offset(offset)
        )

        users = self.session.exec(statement).all()
        self.session.close()
        return users

    def get_one(
        self,
        email: str,
    ) -> UserTable:
        """
        Get one single user by email
        """
        statement = select(UserTable).where(UserTable.email == email)
        user = self.session.exec(statement).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        else:
            self.session.close()
            return user

    def login(self, data: LoginRequest):
        """
        Provided email and password, returns token to login
        """
        email = data.email.lower()
        password = data.password
        statement = select(UserTable).where(
            UserTable.email == email, UserTable.password == password
        )
        user = self.session.exec(statement).first()
        if user:
            access_token, data = encode_access_token(password, email)
            return access_token, data
        else:
            raise BinbotErrors("Invalid email or password")

    def add(self, data: UserDetails):
        try:
            self.get_one(email=data.email)
        except HTTPException as error:
            if error.status_code == 404:
                pass
            else:
                raise error

        user_details = UserTable(
            email=data.email,
            full_name=data.full_name,
            password=data.password,
            username=data.username,
            bio=data.bio,
            role=data.role,
        )
        password = pbkdf2_sha256.encrypt(data.password, rounds=20000, salt_size=16)
        user_details.password = password

        user_table_model = UserTable.model_dump(user_details)
        self.session.add(user_table_model)
        self.session.commit()
        self.session.refresh(user_table_model)
        self.session.close()

        return user_table_model

    def edit(self, data: UserDetails):
        user = self.get_one(email=data.email)
        user.sqlmodel_update(data)

        user.password = pbkdf2_sha256.encrypt(data.password, rounds=20000, salt_size=16)

        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        self.session.close()

        return user

    def delete(self, email):
        user = self.get_one(email=email)
        self.session.delete(user)
        self.session.commit()
        self.session.close()
        return email
