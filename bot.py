import nextcord
from nextcord.ext import commands, tasks
from flask import Flask
import threading
import requests
from datetime import datetime
import pymongo

# MongoDB 연결 설정
mongo_client = pymongo.MongoClient("your_mongodb_connection_string")
db = mongo_client["attendance_db"]  # 데이터베이스 이름
attendance_collection = db["attendance"]  # 출근 기록 컬렉션
cumulative_collection = db["cumulative_time"]  # 누적 시간 컬렉션

# Flask 웹 서버 설정
app = Flask(__name__)

@app.route("/")
def status_page():
    return "<h1>봇이 정상 구동 중입니다! 명령어를 사용하셔도 괜찮습니다!</h1>"

def run_flask():
    app.run(host="0.0.0.0", port=5000)

# Nextcord 봇 설정
intents = nextcord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

ADMIN_USER_IDS = ["123456789012345678", "987654321098765432"]  # 관리자 ID 리스트
STATUS_PAGE_URL = "http://localhost:5000"  # 웹사이트 URL (로컬 또는 배포된 주소)

# 10초마다 웹사이트 상태 확인
@tasks.loop(seconds=10)
async def check_website_status():
    try:
        response = requests.get(STATUS_PAGE_URL)
        if response.status_code == 200:
            print("✅ 웹사이트가 정상적으로 작동 중입니다.")
        else:
            print(f"⚠️ 웹사이트 상태 이상: HTTP {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ 웹사이트 연결 실패: {e}")

# 출근 명령어
@bot.slash_command(name="출근", description="출근 기록을 생성합니다.")
async def 출근(interaction: nextcord.Interaction, 분류: str, 배차차량: str, 소속: str):
    user_id = str(interaction.user.id)
    username = interaction.user.name

    now = datetime.now()
    check_in_time = now.strftime("%H:%M:%S")
    date = now.strftime("%Y-%m-%d")

    # 출근 기록 저장
    attendance_collection.insert_one({
        "user_id": user_id,
        "username": username,
        "date": date,
        "classification": 분류,
        "vehicle": 배차차량,
        "department": 소속,
        "check_in_time": check_in_time,
        "check_out_time": "기록중"
    })

    # 누적 시간 확인 및 업데이트
    cumulative_data = cumulative_collection.find_one({"user_id": user_id})

    if not cumulative_data:
        # 처음 실행한 사용자라면 누적 시간 추가하지 않음
        cumulative_collection.insert_one({
            "user_id": user_id,
            "username": username,
            "cumulative_hours": 0  # 초기값은 0
        })
        await interaction.response.send_message(
            f"✅ 출근 처리가 완료되었습니다!\n\n"
            f"**출근일자**: {date}\n"
            f"**분류**: {분류}\n"
            f"**배차차량**: {배차차량}\n"
            f"**소속**: {소속}\n"
            f"📊 **누적 시간**: 아직 기록 없음",
            ephemeral=False
        )
    else:
        await interaction.response.send_message(
            f"✅ 출근 처리가 완료되었습니다!\n\n"
            f"**출근일자**: {date}\n"
            f"**분류**: {분류}\n"
            f"**배차차량**: {배차차량}\n"
            f"**소속**: {소속}\n"
            f"📊 **누적 시간**: {cumulative_data['cumulative_hours']}시간",
            ephemeral=False
        )

# 퇴근 명령어
@bot.slash_command(name="퇴근", description="퇴근 기록을 처리합니다.")
async def 퇴근(interaction: nextcord.Interaction):
    user_id = str(interaction.user.id)
    now = datetime.now()
    check_out_time = now.strftime("%H:%M:%S")

    # 출근 기록 찾기 및 퇴근 시간 업데이트
    attendance_data = attendance_collection.find_one_and_update(
        {"user_id": user_id, "check_out_time": "기록중"},
        {"$set": {"check_out_time": check_out_time}},
        return_document=True
    )

    if not attendance_data:
        await interaction.response.send_message(
            "❌ 출근 기록이 없습니다. 먼저 `/출근` 명령어를 실행해주세요.",
            ephemeral=True
        )
        return

    check_in_time = datetime.strptime(attendance_data["check_in_time"], "%H:%M:%S")
    check_out_time_dt = datetime.strptime(check_out_time, "%H:%M:%S")
    duration_hours = (check_out_time_dt - check_in_time).total_seconds() / 3600

    if duration_hours <= 0:
        await interaction.response.send_message(
            "❌ 퇴근 시간이 출근 시간보다 빠릅니다. 올바른 데이터를 확인해주세요.",
            ephemeral=True
        )
        return

    # 누적 시간 업데이트
    cumulative_data = cumulative_collection.find_one_and_update(
        {"user_id": user_id},
        {"$inc": {"cumulative_hours": duration_hours}},
        upsert=True,
        return_document=True
    )

    await interaction.response.send_message(
        f"✅ 퇴근 처리가 완료되었습니다!\n\n"
        f"📊 **누적 시간**: {round(cumulative_data['cumulative_hours'], 2)}시간",
        ephemeral=False
    )

# 조기 초기화 명령어 (확인창 포함)
@bot.slash_command(name="조기초기화", description="모든 직원의 출근 누적 시간을 즉시 초기화합니다.")
async def 조기초기화(interaction: nextcord.Interaction):
    if str(interaction.user.id) not in ADMIN_USER_IDS:
        await interaction.response.send_message(
            "❌ 이 명령어를 실행할 권한이 없습니다.",
            ephemeral=True
        )
        return

    embed = nextcord.Embed(title="⚠️ 조기 초기화 확인", description="정말로 모든 직원의 출근 누적 시간을 초기화하시겠습니까?", color=0xFF0000)
    view = nextcord.ui.View()

    async def confirm_callback(button_interaction):
        cumulative_collection.update_many({}, {"$set": {"cumulative_hours": 0}})
        await button_interaction.response.edit_message(content="✅ 모든 직원의 출근 누적 시간이 초기화되었습니다.", embed=None, view=None)

    async def cancel_callback(button_interaction):
        await button_interaction.response.edit_message(content="❌ 초기화 작업이 취소되었습니다.", embed=None, view=None)

    confirm_button = nextcord.ui.Button(label="네", style=nextcord.ButtonStyle.danger)
    confirm_button.callback = confirm_callback

    cancel_button = nextcord.ui.Button(label="아니오", style=nextcord.ButtonStyle.secondary)
    cancel_button.callback = cancel_callback

    view.add_item(confirm_button)
    view.add_item(cancel_button)

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# Flask 서버 실행 (별도 스레드에서 실행)
flask_thread = threading.Thread(target=run_flask)
flask_thread.start()

# 봇 준비 이벤트 및 웹사이트 상태 확인 작업 시작
@bot.event
async def on_ready():
    print(f"{bot.user} 봇이 준비되었습니다!")
    check_website_status.start()

# 봇 실행
bot.run("your_discord_bot_token")
