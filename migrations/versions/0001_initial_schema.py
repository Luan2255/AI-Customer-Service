"""Create customer service schema and built-in intents."""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

INTENTS = [
    ("duvida", "Perguntas gerais sobre produtos e serviços."),
    ("reclamacao", "Insatisfação ou relato de experiência negativa."),
    ("suporte", "Ajuda técnica e resolução de problemas."),
    ("financeiro", "Cobranças, pagamentos, faturas e reembolsos."),
    ("vendas", "Interesse em produtos, planos ou contratação."),
    ("cancelamento", "Solicitações de cancelamento ou encerramento."),
    ("outros", "Mensagens sem correspondência com outra categoria."),
]


def upgrade() -> None:
    """Create all application tables, indexes, relationships, and built-in intents."""
    # Store optional customer identity records first so conversations can reference them.
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # Seed the intent catalog before messages begin referencing intent identifiers.
    op.create_table(
        "intents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("description", sa.String(length=240), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_intents_name", "intents", ["name"], unique=True)

    # Track conversation ownership and persistent human-escalation state.
    op.create_table(
        "conversations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="open", nullable=False),
        sa.Column("human_required", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("escalation_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])

    # Store reusable FAQ entries supplied to the assistant as relevant context.
    op.create_table(
        "knowledge_base",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("question", sa.String(length=500), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_base_category", "knowledge_base", ["category"])
    op.create_index("ix_knowledge_base_is_active", "knowledge_base", ["is_active"])

    # Persist each user/assistant turn and link it to its conversation and intent.
    op.create_table(
        "messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("intent_id", sa.Integer(), nullable=True),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["intent_id"], ["intents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index("ix_messages_created_at", "messages", ["created_at"])
    op.create_index("ix_messages_intent_id", "messages", ["intent_id"])

    # Make the supported intent categories available immediately after migration.
    intents = sa.table("intents", sa.column("name", sa.String), sa.column("description", sa.String))
    op.bulk_insert(intents, [{"name": name, "description": description} for name, description in INTENTS])


def downgrade() -> None:
    """Drop dependent tables and indexes in reverse dependency order."""
    # Remove message references before dropping their parent and catalog tables.
    op.drop_index("ix_messages_intent_id", table_name="messages")
    op.drop_index("ix_messages_created_at", table_name="messages")
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_knowledge_base_is_active", table_name="knowledge_base")
    op.drop_index("ix_knowledge_base_category", table_name="knowledge_base")
    op.drop_table("knowledge_base")
    op.drop_index("ix_conversations_user_id", table_name="conversations")
    op.drop_table("conversations")
    op.drop_index("ix_intents_name", table_name="intents")
    op.drop_table("intents")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")