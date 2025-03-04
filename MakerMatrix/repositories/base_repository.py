from sqlmodel import SQLModel, Session, select
from typing import TypeVar, Generic, Type, Optional, List

T = TypeVar('T', bound=SQLModel)

class BaseRepository(Generic[T]):
    def __init__(self, model_class: Type[T]):
        self.model_class = model_class

    def get_by_id(self, session: Session, id: str) -> Optional[T]:
        return session.exec(select(self.model_class).where(self.model_class.id == id)).first()

    def get_all(self, session: Session) -> List[T]:
        return session.exec(select(self.model_class)).all()

    def create(self, session: Session, model: T) -> T:
        session.add(model)
        session.commit()
        session.refresh(model)
        return model

    def update(self, session: Session, model: T) -> T:
        session.add(model)
        session.commit()
        session.refresh(model)
        return model

    def delete(self, session: Session, id: str) -> bool:
        model = self.get_by_id(session, id)
        if model:
            session.delete(model)
            session.commit()
            return True
        return False
