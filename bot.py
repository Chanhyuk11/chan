import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

GUILD_ID = 1326534226497110069  # 서버 ID 입력

# 역할별 명령어 접근 제한을 위한 함수
async def check_role_permissions(interaction, allowed_roles):
    user_roles = [role.name for role in interaction.user.roles]
    if not any(role in user_roles for role in allowed_roles):
        await interaction.response.send_message("이 명령어는 해당 역할에서 사용할 수 없습니다.", ephemeral=True)
        return False
    return True

# 봇이 준비 완료되었을 때 실행되는 이벤트
@bot.event
async def on_ready():
    print(f"봇 로그인됨: {bot.user}")
    try:
        # 슬래시 명령어 동기화
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"✅ {len(synced)}개 명령어 동기화됨")
    except Exception as e:
        print(f"명령어 동기화 오류: {e}")

# 출퇴근 기록
user_time_data = {}

@bot.tree.command(name="출근", description="출근 시간을 기록합니다.", guild=discord.Object(id=GUILD_ID))
async def check_in(interaction: discord.Interaction):
    if not await check_role_permissions(interaction, ['실습', '주임', '선임', '담당관', '팀장', '경리팀', '차량관리팀', '본부장', '임원', '대표']):
        return
    user = interaction.user
    user_time_data[user.id] = {"출근": interaction.created_at}
    await interaction.response.send_message(f"{user.name} 님의 출근 시간이 기록되었습니다.")

@bot.tree.command(name="퇴근", description="퇴근 시간을 기록합니다.", guild=discord.Object(id=GUILD_ID))
async def check_out(interaction: discord.Interaction):
    if not await check_role_permissions(interaction, ['실습', '주임', '선임', '담당관', '팀장', '경리팀', '차량관리팀', '본부장', '임원', '대표']):
        return
    user = interaction.user
    if user.id not in user_time_data or "퇴근" in user_time_data[user.id]:
        await interaction.response.send_message(f"{user.name} 님은 이미 퇴근 시간을 기록하셨거나 출근하지 않았습니다.")
        return
    user_time_data[user.id]["퇴근"] = interaction.created_at
    check_in_time = user_time_data[user.id]["출근"]
    work_duration = interaction.created_at - check_in_time
    await interaction.response.send_message(f"{user.name} 님의 퇴근 시간이 기록되었습니다. 근무 시간: {work_duration}.")

# 근무시간 조회 (자기 자신만)
@bot.tree.command(name="근무시간확인", description="자신의 근무 시간을 확인합니다.", guild=discord.Object(id=GUILD_ID))
async def check_work_time(interaction: discord.Interaction):
    if interaction.user.id != interaction.user.id:
        await interaction.response.send_message("자신의 근무시간만 조회 가능합니다.", ephemeral=True)
        return
    user = interaction.user
    if user.id not in user_time_data or "퇴근" not in user_time_data[user.id]:
        await interaction.response.send_message(f"{user.name} 님은 퇴근 기록이 없습니다.")
        return
    check_in_time = user_time_data[user.id]["출근"]
    check_out_time = user_time_data[user.id]["퇴근"]
    work_duration = check_out_time - check_in_time
    await interaction.response.send_message(f"{user.name} 님의 근무 시간: {work_duration}.")

# 차량 관리
car_list = {
    "차량1": {"모델": "2018 Hyundai Sonata", "상태": "정상"},
    "차량2": {"모델": "2020 Hyundai Grandeur", "상태": "사고"},
}

@bot.tree.command(name="차량목록", description="차량 목록을 조회합니다.", guild=discord.Object(id=GUILD_ID))
async def car_list_command(interaction: discord.Interaction):
    if not await check_role_permissions(interaction, ['차량관리팀', '관리자', '본부장', '임원', '대표']):
        return
    car_info = "\n".join([f"{key}: {value['모델']} - {value['상태']}" for key, value in car_list.items()])
    await interaction.response.send_message(f"차량 목록:\n{car_info}")

@bot.tree.command(name="차량상태", description="차량의 상태를 변경합니다.", guild=discord.Object(id=GUILD_ID))
async def update_car_status(interaction: discord.Interaction, car_name: str, status: str):
    if not await check_role_permissions(interaction, ['차량관리팀', '관리자', '본부장', '임원', '대표']):
        return
    if car_name in car_list:
        car_list[car_name]["상태"] = status
        await interaction.response.send_message(f"{car_name}의 상태가 '{status}'로 변경되었습니다.")
    else:
        await interaction.response.send_message(f"{car_name} 차량이 존재하지 않습니다.")

# 배차 (중복 배차 방지)
@bot.tree.command(name="배차", description="차량을 기사에게 배차합니다.", guild=discord.Object(id=GUILD_ID))
async def assign_car(interaction: discord.Interaction, car_name: str):
    if not await check_role_permissions(interaction, ['기사', '관리자', '본부장', '임원', '대표']):
        return
    if car_name in car_list and car_list[car_name]["상태"] == "정상":
        car_list[car_name]["상태"] = "배차중"
        await interaction.response.send_message(f"{car_name} 차량이 배차되었습니다.")
    else:
        await interaction.response.send_message(f"{car_name} 차량은 배차할 수 없습니다.")

# 관리자 등록
@bot.tree.command(name="관리자등록", description="관리자를 등록합니다.", guild=discord.Object(id=GUILD_ID))
async def register_admin(interaction: discord.Interaction, admin_name: str):
    if not await check_role_permissions(interaction, ['관리자', '본부장', '임원', '대표']):
        return
    # 관리자 등록 로직
    await interaction.response.send_message(f"{admin_name} 님이 관리자 권한을 받았습니다.")

# 기사 등록
@bot.tree.command(name="기사등록", description="기사를 등록합니다.", guild=discord.Object(id=GUILD_ID))
async def register_driver(interaction: discord.Interaction, driver_name: str):
    if not await check_role_permissions(interaction, ['관리자', '본부장', '임원', '대표']):
        return
    # 기사 등록 로직
    await interaction.response.send_message(f"{driver_name} 님이 기사로 등록되었습니다.")

# 크루 등록
@bot.tree.command(name="크루등록", description="크루를 등록합니다.", guild=discord.Object(id=GUILD_ID))
async def register_crew(interaction: discord.Interaction, crew_name: str):
    if not await check_role_permissions(interaction, ['관리자', '본부장', '임원', '대표']):
        return
    # 크루 등록 로직
    await interaction.response.send_message(f"{crew_name} 님이 크루로 등록되었습니다.")

# 별명 변경
@bot.tree.command(name="별명변경", description="별명을 변경하고 역할을 추가합니다.", guild=discord.Object(id=GUILD_ID))
async def change_nickname(interaction: discord.Interaction, new_nickname: str, role_name: str):
    if not await check_role_permissions(interaction, ['관리자', '본부장', '임원', '대표']):
        return
    await interaction.user.edit(nick=new_nickname)
    # 역할 추가 로직
    await interaction.user.add_roles(discord.utils.get(interaction.guild.roles, name=role_name))
    await interaction.response.send_message(f"{new_nickname}로 별명이 변경되었고, 역할 '{role_name}'이 추가되었습니다.")

# 뮤트 (관리자만)
@bot.tree.command(name="뮤트", description="유저를 음소거합니다.", guild=discord.Object(id=GUILD_ID))
async def mute_user(interaction: discord.Interaction, member: discord.Member, reason: str = "명시되지 않은 이유"):
    if not await check_role_permissions(interaction, ['관리자', '본부장', '임원', '대표']):
        return
    if interaction.user.guild_permissions.mute_members:
        await member.edit(mute=True)
        await interaction.response.send_message(f"{member.name} 님을 뮤트했습니다. 사유: {reason}")
    else:
        await interaction.response.send_message("뮤트 권한이 없습니다.")

# 차단 (관리자만)
@bot.tree.command(name="차단", description="유저를 차단합니다.", guild=discord.Object(id=GUILD_ID))
async def block_user(interaction: discord.Interaction, member: discord.Member, reason: str = "명시되지 않은 이유"):
    if not await check_role_permissions(interaction, ['관리자', '본부장', '임원', '대표']):
        return
    await member.ban(reason=reason)
    await interaction.response.send_message(f"{member.name} 님을 차단했습니다. 사유: {reason}")

# 추방 (관리자만)
@bot.tree.command(name="추방", description="유저를 추방합니다.", guild=discord.Object(id=GUILD_ID))
async def kick_user(interaction: discord.Interaction, member: discord.Member, reason: str = "명시되지 않은 이유"):
    if not await check_role_permissions(interaction, ['관리자', '본부장', '임원', '대표']):
        return
    await member.kick(reason=reason)
    await interaction.response.send_message(f"{member.name} 님을 추방했습니다. 사유: {reason}")

# 역할 생성
@bot.tree.command(name="역할생성", description="필요한 역할을 자동으로 생성합니다.", guild=discord.Object(id=GUILD_ID))
async def create_roles(interaction: discord.Interaction):
    if not await check_role_permissions(interaction, ['관리자', '본부장', '임원', '대표']):
        return
    role_names = ["실습", "주임", "선임", "담당관", "팀장", "경리팀", "차량관리팀", "본부장", "임원", "대표"]
    for role_name in role_names:
        await interaction.guild.create_role(name=role_name)
    await interaction.response.send_message(f"필요한 역할들이 생성되었습니다.")

# 봇 실행
bot.run("MTM2MTI3NTYwMzUwODI2NTEwMA.GsKv9-.uN_g56dO-i0Mpkx6o06llvIhz1JYb4kpJ1yIGs")
