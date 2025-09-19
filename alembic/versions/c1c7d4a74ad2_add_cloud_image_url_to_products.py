"""add_cloud_image_url_to_products

Revision ID: c1c7d4a74ad2
Revises: abeab2be2368
Create Date: 2025-09-19 04:26:03.793633

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1c7d4a74ad2'
down_revision = 'abeab2be2368'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add cloud_image_url column to products table
    op.add_column('products', sa.Column('cloud_image_url', sa.String(length=1000), nullable=True))


def downgrade() -> None:
    # Remove cloud_image_url column from products table
    op.drop_column('products', 'cloud_image_url')
