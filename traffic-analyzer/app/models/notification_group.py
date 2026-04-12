from app.extensions.extensions import db

group_members = db.Table(
    "notification_group_members",
    db.Column("group_id", db.Integer, db.ForeignKey("notification_groups.id"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
)


class NotificationGroup(db.Model):
    __tablename__ = "notification_groups"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(300))
    is_active = db.Column(db.Boolean, default=True)
    severity_filter = db.Column(db.String(200), default="high,critical")
    extra_emails = db.Column(db.Text, default="")
    members = db.relationship("User", secondary=group_members, backref="notification_groups", lazy="joined")

    @property
    def all_emails(self):
        emails = [u.email for u in self.members]
        if self.extra_emails:
            emails += [e.strip() for e in self.extra_emails.split(",") if e.strip()]
        return list(set(emails))

    @property
    def severity_list(self):
        return [s.strip() for s in self.severity_filter.split(",") if s.strip()]

    def __str__(self):
        return self.name
