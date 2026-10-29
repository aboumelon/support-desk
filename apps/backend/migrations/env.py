from alembic import context
from sqlalchemy import create_engine

from supportdesk.config import get_settings
from supportdesk.infrastructure.database import Base
from supportdesk.modules.assistant import models as assistant
from supportdesk.modules.audit import models as audit
from supportdesk.modules.conversations import models as conversations
from supportdesk.modules.identity import models as identity
from supportdesk.modules.jobs import models as jobs
from supportdesk.modules.knowledge import models as knowledge
from supportdesk.modules.messaging import models as messaging
from supportdesk.modules.workspaces import models as workspaces

assert (
    assistant
    and knowledge
    and audit
    and identity
    and workspaces
    and conversations
    and messaging
    and jobs
)
target_metadata = Base.metadata
if context.is_offline_mode():
    context.configure(
        url=get_settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    with create_engine(get_settings().database_url).connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
