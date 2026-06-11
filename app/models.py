from app import db
from datetime import datetime


class Vacancy(db.Model):
    __tablename__ = 'vacancies'

    id = db.Column(db.String(100), primary_key=True)
    source = db.Column(db.String(50))
    title = db.Column(db.String(500))
    company = db.Column(db.String(200))
    salary = db.Column(db.String(100))
    city = db.Column(db.String(100))
    url = db.Column(db.String(500))
    published = db.Column(db.String(50))
    snippet_requirement = db.Column(db.Text)
    snippet_responsibility = db.Column(db.Text)
    direction = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f'<Vacancy {self.id}: {self.title}>'

    def to_dict(self):
        board_card = self.board_card if hasattr(self, 'board_card') else None

        return {
            'id': self.id,
            'source': self.source,
            'title': self.title,
            'company': self.company,
            'salary': self.salary,
            'city': self.city,
            'url': self.url,
            'published': self.published,
            'snippet_requirement': self.snippet_requirement,
            'snippet_responsibility': self.snippet_responsibility,
            'direction': self.direction,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'board_status': board_card.status if board_card else 'new',
            'starred': getattr(board_card, 'starred', False) if board_card else False,
            'postponed': board_card.is_postponed if board_card else False,
            'notes': board_card.notes if board_card else '',
            'postponed_until': board_card.postponed_until.isoformat() if board_card and board_card.postponed_until else None,
        }


class BoardCard(db.Model):
    __tablename__ = 'board_cards'

    id = db.Column(db.Integer, primary_key=True)
    vacancy_id = db.Column(db.String(50), db.ForeignKey('vacancies.id'), unique=True)
    status = db.Column(db.String(50), default='new')
    notes = db.Column(db.Text)
    starred = db.Column(db.Boolean, default=False)
    is_postponed = db.Column(db.Boolean, default=False)
    postponed_until = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    vacancy = db.relationship('Vacancy', backref=db.backref('board_card', uselist=False))

    def __repr__(self):
        return f'<BoardCard {self.id}: {self.vacancy_id} - {self.status}>'


class UserProfile(db.Model):
    __tablename__ = 'user_profiles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    specialty = db.Column(db.String(200))
    education = db.Column(db.Text)
    experience = db.Column(db.Text)
    skills = db.Column(db.Text)
    languages = db.Column(db.String(200))
    preferred_directions = db.Column(db.String(200))
    expected_salary = db.Column(db.String(100))
    about = db.Column(db.Text)
    projects = db.Column(db.Text)
    contacts = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<UserProfile {self.id}: {self.name or "Не заполнен"}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name or '',
            'specialty': self.specialty or '',
            'education': self.education or '',
            'experience': self.experience or '',
            'skills': self.skills or '',
            'languages': self.languages or '',
            'preferred_directions': self.preferred_directions or '',
            'expected_salary': self.expected_salary or '',
            'about': self.about or '',
            'projects': self.projects or '',
            'contacts': self.contacts or '',
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class CoverLetterTemplate(db.Model):
    __tablename__ = 'cover_letter_templates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), default="default")
    template_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SearchQuery(db.Model):
    __tablename__ = 'search_queries'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, default=True)

class StopWord(db.Model):
    __tablename__ = 'stopwords'
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), nullable=False, unique=True)
    category = db.Column(db.String(50), default='general')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TelegramUser(db.Model):
    __tablename__ = 'telegram_users'
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.BigInteger, unique=True, nullable=False)
    username = db.Column(db.String(100))
    first_name = db.Column(db.String(100))
    subscribed = db.Column(db.Boolean, default=True)
    notify_new = db.Column(db.Boolean, default=True)
    notify_match = db.Column(db.Boolean, default=True)
    min_match_percent = db.Column(db.Integer, default=70)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_notified = db.Column(db.DateTime, nullable=True)