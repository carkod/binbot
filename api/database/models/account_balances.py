from typing import Optional
from uuid import UUID, uuid4
from sqlalchemy import BigInteger, Column
from database.utils import timestamp
from sqlmodel import Relationship, SQLModel, Field


class BalancesTable(SQLModel, table=True):
    """
    Balances table to store user balances
    """

    __tablename__ = "balances"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        unique=True,
        index=True,
    )
    timestamp: int = Field(
        default_factory=timestamp, sa_column=Column(BigInteger(), index=True)
    )
    asset: str = Field(index=True, nullable=False)
    quantity: Optional[float] = Field(default=0, description="local quantity (asset)")

    # Relationships
    consolidated_balances_id: Optional[int] = Field(
        default=None,
        foreign_key="consolidated_balances.id",
        ondelete="CASCADE",
        sa_type=BigInteger,
    )
    consolidated_balances: Optional["ConsolidatedBalancesTable"] = Relationship(
        back_populates="balances"
    )


class ConsolidatedBalancesTable(SQLModel, table=True):
    """
      Replacement of old MongoDB balances collection
      future plans include consolidation with all connected exchanges.

      Should return the same as previous balances collection

      {
      _id: ObjectId('60eb374383f341ddc54b9411'),
      time: '2021-07-11',
      balances: [
        { asset: 'BTC', free: 0.00333733, locked: 0 },
        { asset: 'BNB', free: 0.00096915, locked: 0 },
        { asset: 'ZEC', free: 0.191808, locked: 0 },
        { asset: 'KMD', free: 37.81, locked: 0 },
        { asset: 'DUSK', free: 294, locked: 0 },
        { asset: 'GBP', free: 9.87392004, locked: 0 },
        { asset: 'NFT', free: 26387.614932, locked: 0 }
      ],
      estimated_total_btc: 0.008809462952797817,
      estimated_total_gbp: 203.25007925973117
    }

      - id is a unique timestamp to support series. This should be ingested as before, once per day

    """

    __tablename__ = "consolidated_balances"

    id: int = Field(
        default_factory=timestamp,
        sa_column=Column(BigInteger(), primary_key=True, index=True),
    )
    balances: list[BalancesTable] = Relationship(
        sa_relationship_kwargs={"lazy": "joined", "single_parent": True},
    )
    estimated_total_fiat: float = Field(
        default=0,
        description="This is derived from free * price of fiat, which is determined in autotrade",
    )


class StagingBalancesTable(SQLModel, table=True):
    """
    Balances table to store user balances
    """

    __tablename__ = "staging_balances"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        unique=True,
        index=True,
    )
    timestamp: int = Field(
        default_factory=timestamp, sa_column=Column(BigInteger(), index=True)
    )
    asset: str = Field(index=True, nullable=False)
    quantity: Optional[float] = Field(default=0, description="local quantity (asset)")

    # Relationships
    consolidated_balances_id: Optional[int] = Field(
        default=None,
        foreign_key="staging_consolidated_balances.id",  # <-- fixed foreign key
        ondelete="CASCADE",
        sa_type=BigInteger,
    )
    consolidated_balances: Optional["StagingConsolidatedBalancesTable"] = Relationship(
        back_populates="balances"
    )


class StagingConsolidatedBalancesTable(SQLModel, table=True):
    """
    Staging version of consolidated balances table
    """

    __tablename__ = "staging_consolidated_balances"

    id: int = Field(
        default_factory=timestamp,
        sa_column=Column(BigInteger(), primary_key=True, index=True),
    )
    balances: list[StagingBalancesTable] = Relationship(
        sa_relationship_kwargs={"lazy": "joined", "single_parent": True},
    )
    estimated_total_fiat: float = Field(
        default=0,
        description="This is derived from free * price of fiat, which is determined in autotrade",
    )
