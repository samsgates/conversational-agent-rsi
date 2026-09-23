"""initial schema"""
from alembic import op
from apps.control_api.models import Base
revision="0001"
down_revision=None
branch_labels=None
depends_on=None
def upgrade():
    bind=op.get_bind()
    Base.metadata.create_all(bind=bind)
def downgrade():
    bind=op.get_bind()
    Base.metadata.drop_all(bind=bind)
