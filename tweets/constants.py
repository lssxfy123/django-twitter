class TweetPhotoStatus:
    PENDING = 0  # 等待
    APPROVED = 1  # 审核通过
    REJECTED = 2  # 被拒绝


TWEET_PHOTO_STATUS_CHOICES = (
    (TweetPhotoStatus.PENDING, 'Pending'),
    (TweetPhotoStatus.APPROVED, 'Approved'),
    (TweetPhotoStatus.REJECTED, 'Rejected'),
)
