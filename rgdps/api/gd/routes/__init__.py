from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends
from fastapi.responses import PlainTextResponse
from fastapi_limiter.depends import RateLimiter

from rgdps import settings

from . import leaderboards
from . import level_comments
from . import levels
from . import messages
from . import misc
from . import rewards
from . import save_data
from . import user_comments
from . import user_relationships
from . import users

router = APIRouter(
    prefix=settings.APP_URL_PREFIX,
    default_response_class=PlainTextResponse,
)

router.add_api_route(
    "/accounts/registerGJAccount.php",
    users.register_post,
    methods=["POST"],
    dependencies=[
        Depends(RateLimiter(times=10, minutes=10)),
    ],
)

router.add_api_route(
    "/",
    misc.main_get,
)

router.add_api_route(
    "/getGJUserInfo20.php",
    users.user_info_get,
    methods=["POST"],
)

router.add_api_route(
    "/accounts/loginGJAccount.php",
    users.login_post,
    methods=["POST"],
)

router.add_api_route(
    "/updateGJUserScore22.php",
    users.user_info_update,
    methods=["POST"],
)

router.add_api_route(
    "/getGJFriendRequests20.php",
    user_relationships.friend_requests_get,
    methods=["POST"],
)

router.add_api_route(
    "/uploadFriendRequest20.php",
    user_relationships.friend_request_post,
    methods=["POST"],
    dependencies=[
        Depends(RateLimiter(times=1, seconds=30)),
    ],
)

router.add_api_route(
    "/readGJFriendRequest20.php",
    user_relationships.friend_request_read,
    methods=["POST"],
)

router.add_api_route(
    "/deleteGJFriendRequests20.php",
    user_relationships.friend_requests_delete,
    methods=["POST"],
)

router.add_api_route(
    "/acceptGJFriendRequest20.php",
    user_relationships.friend_request_accept,
    methods=["POST"],
)

router.add_api_route(
    "/getGJUserList20.php",
    user_relationships.user_relationships_get,
    methods=["POST"],
)

router.add_api_route(
    "/removeGJFriend20.php",
    user_relationships.friend_remove_post,
    methods=["POST"],
)

router.add_api_route(
    "/blockGJUser20.php",
    user_relationships.block_user_post,
    methods=["POST"],
    dependencies=[
        Depends(RateLimiter(times=1, seconds=30)),
    ],
)

router.add_api_route(
    "/unblockGJUser20.php",
    user_relationships.unblock_user_post,
    methods=["POST"],
)

router.add_api_route(
    "/uploadGJAccComment20.php",
    user_comments.user_comments_post,
    methods=["POST"],
    dependencies=[
        Depends(RateLimiter(times=4, minutes=1)),
    ],
)

router.add_api_route(
    "/getGJAccountComments20.php",
    user_comments.user_comments_get,
    methods=["POST"],
)

router.add_api_route(
    "/updateGJAccSettings20.php",
    users.user_settings_update,
    methods=["POST"],
)

router.add_api_route(
    "/getGJSongInfo.php",
    levels.song_info_get,
    methods=["POST"],
)

# Geometry Dash forces these 2 to be prefixed with /database
router.add_api_route(
    "/database/accounts/syncGJAccountNew.php",
    save_data.save_data_get,
    methods=["POST"],
)

router.add_api_route(
    "/database/accounts/backupGJAccountNew.php",
    save_data.save_data_post,
    methods=["POST"],
    dependencies=[
        Depends(RateLimiter(times=1, minutes=5)),
    ],
)

router.add_api_route(
    "/getAccountURL.php",
    save_data.get_save_endpoint,
    methods=["POST"],
)

router.add_api_route(
    "/uploadGJLevel21.php",
    levels.level_post,
    methods=["POST"],
    # TODO: Tweak based on average user behaviour. May be way too high.
    dependencies=[
        Depends(RateLimiter(times=3, minutes=10)),
    ],
)

router.add_api_route(
    "/getGJLevels21.php",
    levels.levels_get,
    methods=["POST"],
)

router.add_api_route(
    "/downloadGJLevel22.php",
    levels.level_get,
    methods=["POST"],
    # TODO: Tweak based on average user behaviour. May be too low.
    dependencies=[
        Depends(RateLimiter(times=100, minutes=10)),
    ],
)

router.add_api_route(
    "/getGJScores20.php",
    leaderboards.leaderboard_get,
    methods=["POST"],
)

router.add_api_route(
    "/likeGJItem211.php",
    user_comments.like_target_post,
    methods=["POST"],
    dependencies=[
        Depends(RateLimiter(times=50, minutes=10)),
    ],
)

router.add_api_route(
    "/deleteGJAccComment20.php",
    user_comments.user_comment_delete,
    methods=["POST"],
)

router.add_api_route(
    "/uploadGJComment21.php",
    level_comments.create_comment_post,
    methods=["POST"],
    dependencies=[
        Depends(RateLimiter(times=15, minutes=1)),
    ],
)

router.add_api_route(
    "/requestUserAccess.php",
    users.request_status_get,
    methods=["POST"],
)

router.add_api_route(
    "/getGJComments21.php",
    level_comments.level_comments_get,
    methods=["POST"],
)

router.add_api_route(
    "/getGJMessages20.php",
    messages.messages_get,
    methods=["POST"],
)

router.add_api_route(
    "/uploadGJMessage20.php",
    messages.message_post,
    methods=["POST"],
    dependencies=[
        Depends(RateLimiter(times=5, minutes=5)),
    ],
)

router.add_api_route(
    "/deleteGJMessages20.php",
    messages.message_delete,
    methods=["POST"],
)

router.add_api_route(
    "/downloadGJMessage20.php",
    messages.message_get,
    methods=["POST"],
)


router.add_api_route(
    "/suggestGJStars20.php",
    levels.suggest_level_stars,
    methods=["POST"],
)

router.add_api_route(
    "/getGJCommentHistory.php",
    level_comments.comment_history_get,
    methods=["POST"],
)

router.add_api_route(
    "/deleteGJComment20.php",
    level_comments.level_comment_delete,
    methods=["POST"],
)

router.add_api_route(
    "/getGJRewards.php",
    rewards.daily_chest_get,
    methods=["POST"],
)

router.add_api_route(
    "/getGJUsers20.php",
    users.users_get,
    methods=["POST"],
)

router.add_api_route(
    "/updateGJDesc20.php",
    levels.level_desc_post,
    methods=["POST"],
)

router.add_api_route(
    "/deleteGJLevelUser20.php",
    levels.level_delete_post,
    methods=["POST"],
)

router.add_api_route(
    "/getGJDailyLevel.php",
    levels.daily_level_info_get,
    methods=["POST"],
)

router.add_api_route(
    "/rateGJDemon21.php",
    levels.demon_difficulty_post,
    methods=["POST"],
)

router.add_api_route(
    "/getCustomContentURL.php",
    levels.custom_content_cdn_get,
    methods=["POST"],
)
