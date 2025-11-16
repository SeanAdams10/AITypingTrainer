"""SQLAlchemy ORM models for settings system.

Defines SQLAlchemy models for setting_types and settings tables,
including their history tables following SCD-2 pattern.
"""

from datetime import datetime

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


class SettingTypeModel(Base):
    """SQLAlchemy model for setting_types table.
    
    Represents setting type definitions with validation rules and defaults.
    Follows the schema defined in Settings_req.md.
    """

    __tablename__ = "setting_types"

    setting_type_id = Column(String(6), primary_key=True)
    setting_type_name = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    related_entity_type = Column(
        Text,
        nullable=False,
        # CHECK constraint handled at database level
    )
    data_type = Column(
        Text,
        nullable=False,
        # CHECK constraint handled at database level
    )
    default_value = Column(Text, nullable=True)
    validation_rules = Column(Text, nullable=True)
    is_system = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    row_checksum = Column(LargeBinary, nullable=False)
    created_dt = Column(TIMESTAMP(timezone=True), nullable=False)
    updated_dt = Column(TIMESTAMP(timezone=True), nullable=False)
    created_user_id = Column(UUID(as_uuid=True), nullable=False)
    updated_user_id = Column(UUID(as_uuid=True), nullable=False)

    # Relationships
    settings = relationship("SettingModel", back_populates="setting_type")
    history = relationship(
        "SettingTypeHistoryModel",
        back_populates="setting_type",
        order_by="SettingTypeHistoryModel.version_no",
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "setting_type_id ~ '^[A-Z0-9]{6}$'",
            name="ck_setting_type_id_format",
        ),
        CheckConstraint(
            "related_entity_type IN ('user', 'keyboard', 'global')",
            name="ck_related_entity_type",
        ),
        CheckConstraint(
            "data_type IN ('string', 'integer', 'boolean', 'decimal')",
            name="ck_data_type",
        ),
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<SettingType(id='{self.setting_type_id}', "
            f"name='{self.setting_type_name}')>"
        )


class SettingTypeHistoryModel(Base):
    """SQLAlchemy model for setting_types_history table.
    
    SCD-2 history tracking for setting type changes.
    """

    __tablename__ = "setting_types_history"

    audit_id = Column(BigInteger, primary_key=True, autoincrement=True)
    setting_type_id = Column(
        String(6),
        ForeignKey("setting_types.setting_type_id"),
        nullable=False,
    )
    setting_type_name = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    related_entity_type = Column(Text, nullable=False)
    data_type = Column(Text, nullable=False)
    default_value = Column(Text, nullable=True)
    validation_rules = Column(Text, nullable=True)
    is_system = Column(Boolean, nullable=False)
    is_active = Column(Boolean, nullable=False)
    row_checksum = Column(LargeBinary, nullable=False)
    created_dt = Column(TIMESTAMP(timezone=True), nullable=False)
    updated_dt = Column(TIMESTAMP(timezone=True), nullable=False)
    created_user_id = Column(UUID(as_uuid=True), nullable=False)
    updated_user_id = Column(UUID(as_uuid=True), nullable=False)
    action = Column(Text, nullable=False)
    version_no = Column(Integer, nullable=False)
    valid_from_dt = Column(TIMESTAMP(timezone=True), nullable=False)
    valid_to_dt = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=datetime(9999, 12, 31, 23, 59, 59),
    )
    is_current = Column(Boolean, nullable=False)

    # Relationships
    setting_type = relationship("SettingTypeModel", back_populates="history")

    # Table constraints
    __table_args__ = (
        UniqueConstraint("setting_type_id", "version_no", name="uq_type_version"),
        CheckConstraint("action IN ('I', 'U', 'D')", name="ck_action"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<SettingTypeHistory(id='{self.setting_type_id}', "
            f"version={self.version_no}, action='{self.action}')>"
        )


class SettingModel(Base):
    """SQLAlchemy model for settings table.
    
    Represents individual setting values.
    """

    __tablename__ = "settings"

    setting_id = Column(UUID(as_uuid=True), primary_key=True)
    setting_type_id = Column(
        String(6),
        ForeignKey("setting_types.setting_type_id"),
        nullable=False,
    )
    setting_value = Column(Text, nullable=False)
    related_entity_id = Column(UUID(as_uuid=True), nullable=False)
    row_checksum = Column(LargeBinary, nullable=False)
    created_dt = Column(TIMESTAMP(timezone=True), nullable=False)
    updated_dt = Column(TIMESTAMP(timezone=True), nullable=False)
    created_user_id = Column(UUID(as_uuid=True), nullable=False)
    updated_user_id = Column(UUID(as_uuid=True), nullable=False)

    # Relationships
    setting_type = relationship("SettingTypeModel", back_populates="settings")
    history = relationship(
        "SettingHistoryModel",
        back_populates="setting",
        order_by="SettingHistoryModel.version_no",
    )

    # Table constraints
    __table_args__ = (
        UniqueConstraint(
            "setting_type_id",
            "related_entity_id",
            name="uq_setting_type_entity",
        ),
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<Setting(id='{self.setting_id}', "
            f"type='{self.setting_type_id}')>"
        )


class SettingHistoryModel(Base):
    """SQLAlchemy model for settings_history table.
    
    SCD-2 history tracking for setting changes.
    """

    __tablename__ = "settings_history"

    audit_id = Column(BigInteger, primary_key=True, autoincrement=True)
    setting_id = Column(
        UUID(as_uuid=True),
        ForeignKey("settings.setting_id"),
        nullable=False,
    )
    setting_type_id = Column(String(6), nullable=False)
    setting_value = Column(Text, nullable=False)
    related_entity_id = Column(UUID(as_uuid=True), nullable=False)
    row_checksum = Column(LargeBinary, nullable=False)
    created_dt = Column(TIMESTAMP(timezone=True), nullable=False)
    updated_dt = Column(TIMESTAMP(timezone=True), nullable=False)
    created_user_id = Column(UUID(as_uuid=True), nullable=False)
    updated_user_id = Column(UUID(as_uuid=True), nullable=False)
    action = Column(Text, nullable=False)
    version_no = Column(Integer, nullable=False)
    valid_from_dt = Column(TIMESTAMP(timezone=True), nullable=False)
    valid_to_dt = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=datetime(9999, 12, 31, 23, 59, 59),
    )
    is_current = Column(Boolean, nullable=False)

    # Relationships
    setting = relationship("SettingModel", back_populates="history")

    # Table constraints
    __table_args__ = (
        UniqueConstraint("setting_id", "version_no", name="uq_setting_version"),
        CheckConstraint("action IN ('I', 'U', 'D')", name="ck_action"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<SettingHistory(id='{self.setting_id}', "
            f"version={self.version_no}, action='{self.action}')>"
        )
