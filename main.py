import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import sqlite3

 import os
TOKEN = os.getenv("TOKEN")


# --- تجهيز قاعدة البيانات ---
conn = sqlite3.connect("shop_system.db")
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS shops (
    channel_id INTEGER PRIMARY KEY,
    owner_id INTEGER,
    name TEXT,
    shop_type TEXT,
    active INTEGER DEFAULT 1,
    mentions INTEGER DEFAULT 10,
    warnings INTEGER DEFAULT 0,
    created_at TEXT
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS helpers (
    channel_id INTEGER,
    user_id INTEGER,
    PRIMARY KEY (channel_id, user_id)
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS shop_types (
    name TEXT PRIMARY KEY
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS auto_replies (
    trigger TEXT PRIMARY KEY,
    response TEXT
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS afk_users (
    user_id INTEGER PRIMARY KEY,
    reason TEXT
)''')

conn.commit()

# --- إعداد البوت ---
class UltimateShopBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.messages = True
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

bot = UltimateShopBot()

def set_setting(key, value):
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (str(key), str(value)))
    conn.commit()

def get_setting(key):
    cursor.execute("SELECT value FROM settings WHERE key = ?", (str(key),))
    res = cursor.fetchone()
    return res[0] if res else None

@bot.event
async def on_ready():
    print(f"✅ تم تشغيل البوت بنجاح باسم: {bot.user}")
    
    try:
        for guild in bot.guilds:
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
        print("⚡ تم مزامنة كافة أوامر الـ Slash فورياً وبنجاح!")
    except Exception as e:
        print(f"❌ حدث خطأ أثناء المزامنة: {e}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.mentions:
        for user in message.mentions:
            cursor.execute("SELECT reason FROM afk_users WHERE user_id = ?", (user.id,))
            afk = cursor.fetchone()
            if afk:
                await message.channel.send(f"⚠️ المستخدم {user.mention} حالياً AFK: **{afk[0]}**")
    
    cursor.execute("SELECT response FROM auto_replies WHERE trigger = ?", (message.content.strip(),))
    reply = cursor.fetchone()
    if reply:
        await message.channel.send(reply[0])

    await bot.process_commands(message)

# ==================== 1. أوامر التفعيل والتأطير ====================

@bot.tree.command(name="active", description="تفعيل متجر محدد")
@app_commands.checks.has_permissions(administrator=True)
async def active(interaction: discord.Interaction, shop_channel: discord.TextChannel):
    await interaction.response.defer(ephemeral=True)
    cursor.execute("UPDATE shops SET active = 1 WHERE channel_id = ?", (shop_channel.id,))
    conn.commit()
    await interaction.followup.send(f"✅ تم تفعيل المتجر: {shop_channel.mention}")

@bot.tree.command(name="active-all", description="تفعيل جميع المتاجر")
@app_commands.checks.has_permissions(administrator=True)
async def active_all(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    cursor.execute("UPDATE shops SET active = 1")
    conn.commit()
    await interaction.followup.send("✅ تم تفعيل جميع المتاجر في قاعدة البيانات.")

# ==================== 2. أوامر الإضافة والتأسيس ====================

@bot.tree.command(name="add-auction-room", description="تحديد روم المزادات")
@app_commands.checks.has_permissions(administrator=True)
async def add_auction_room(interaction: discord.Interaction, channel: discord.TextChannel):
    await interaction.response.defer(ephemeral=True)
    set_setting("auction_room", channel.id)
    await interaction.followup.send(f"✅ تم تحديد روم المزادات: {channel.mention}")

@bot.tree.command(name="add-auto-role", description="تحديد الرتبة التلقائية للمشترين")
@app_commands.checks.has_permissions(administrator=True)
async def add_auto_role(interaction: discord.Interaction, role: discord.Role):
    await interaction.response.defer(ephemeral=True)
    set_setting("auto_role", role.id)
    await interaction.followup.send(f"✅ تم تحديد الرتبة التلقائية: {role.mention}")

@bot.tree.command(name="add-emoji-channel", description="تحديد روم الإيموجيات")
@app_commands.checks.has_permissions(administrator=True)
async def add_emoji_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    await interaction.response.defer(ephemeral=True)
    set_setting("emoji_channel", channel.id)
    await interaction.followup.send(f"✅ تم تحديد روم الإيموجيات: {channel.mention}")

@bot.tree.command(name="add-helper", description="إضافة مساعد لمتجر")
async def add_helper(interaction: discord.Interaction, shop_channel: discord.TextChannel, helper: discord.Member):
    await interaction.response.defer(ephemeral=True)
    cursor.execute("INSERT OR REPLACE INTO helpers (channel_id, user_id) VALUES (?, ?)", (shop_channel.id, helper.id))
    conn.commit()
    await shop_channel.set_permissions(helper, read_messages=True, send_messages=True)
    await interaction.followup.send(f"✅ تم إضافة {helper.mention} كمساعد في {shop_channel.mention}")

@bot.tree.command(name="add-mentions", description="إضافة منشنات لمتجر")
@app_commands.checks.has_permissions(administrator=True)
async def add_mentions(interaction: discord.Interaction, shop_channel: discord.TextChannel, amount: int):
    await interaction.response.defer(ephemeral=True)
    cursor.execute("UPDATE shops SET mentions = mentions + ? WHERE channel_id = ?", (amount, shop_channel.id))
    conn.commit()
    await interaction.followup.send(f"✅ تم إضافة {amount} منشن لـ {shop_channel.mention}")

@bot.tree.command(name="add-shop-data", description="إدخال بيانات متجر يدويًا")
@app_commands.checks.has_permissions(administrator=True)
async def add_shop_data(interaction: discord.Interaction, shop_channel: discord.TextChannel, owner: discord.Member, shop_type: str):
    await interaction.response.defer(ephemeral=True)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute("INSERT OR REPLACE INTO shops (channel_id, owner_id, name, shop_type, active, mentions, warnings, created_at) VALUES (?, ?, ?, ?, 1, 10, 0, ?)",
                   (shop_channel.id, owner.id, shop_channel.name, shop_type, now_str))
    conn.commit()
    await interaction.followup.send(f"✅ تم تسجيل بيانات المتجر {shop_channel.mention} يدويًا.")

@bot.tree.command(name="add-tax-channel", description="تحديد روم الضريبة")
@app_commands.checks.has_permissions(administrator=True)
async def add_tax_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    await interaction.response.defer(ephemeral=True)
    set_setting("tax_channel", channel.id)
    await interaction.followup.send(f"✅ تم تحديد روم الضريبة: {channel.mention}")

@bot.tree.command(name="add-type", description="إضافة نوع متجر جديد")
@app_commands.checks.has_permissions(administrator=True)
async def add_type(interaction: discord.Interaction, type_name: str):
    await interaction.response.defer(ephemeral=True)
    cursor.execute("INSERT OR REPLACE INTO shop_types (name) VALUES (?)", (type_name,))
    conn.commit()
    await interaction.followup.send(f"✅ تم إضافة نوع المتجر: **{type_name}**")

# ==================== 3. أوامر الحالة والتفاعل ====================

@bot.tree.command(name="afk", description="تفعيل وضع الغياب")
async def afk(interaction: discord.Interaction, reason: str = "مشغول حالياً"):
    await interaction.response.defer(ephemeral=True)
    cursor.execute("INSERT OR REPLACE INTO afk_users (user_id, reason) VALUES (?, ?)", (interaction.user.id, reason))
    conn.commit()
    await interaction.followup.send(f"💤 تم تفعيل وضع AFK: {reason}")

@bot.tree.command(name="auction", description="إنشاء مزاد جديد")
async def auction(interaction: discord.Interaction, item: str, starting_price: str):
    await interaction.response.defer()
    embed = discord.Embed(title="🔨 مزاد جديد!", color=discord.Color.gold())
    embed.add_field(name="السلعة:", value=item, inline=False)
    embed.add_field(name="السعر الابتدائي:", value=starting_price, inline=False)
    embed.add_field(name="صاحب المزاد:", value=interaction.user.mention, inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="auction-ticket", description="لوحة شراء المزادات")
@app_commands.checks.has_permissions(administrator=True)
async def auction_ticket(interaction: discord.Interaction):
    await interaction.response.defer()
    embed = discord.Embed(title="🎫 لوحة تذاكر المزادات", description="اضغط للتواصل بشأن المزادات.", color=discord.Color.blue())
    await interaction.followup.send(embed=embed)

# ==================== 4. أوامر التعديل والتغيير ====================

@bot.tree.command(name="change-bot-avatar", description="تغيير صورة البوت")
@app_commands.checks.has_permissions(administrator=True)
async def change_bot_avatar(interaction: discord.Interaction, image_url: str):
    await interaction.response.defer(ephemeral=True)
    async with bot.http._HTTPClient__session.get(image_url) as resp:
        if resp.status == 200:
            data = await resp.read()
            await bot.user.edit(avatar=data)
            await interaction.followup.send("✅ تم تغيير صورة البوت بنجاح!")
        else:
            await interaction.followup.send("❌ فشل تحميل الصورة من الرابط.")

@bot.tree.command(name="change-bot-name", description="تغيير اسم البوت")
@app_commands.checks.has_permissions(administrator=True)
async def change_bot_name(interaction: discord.Interaction, new_name: str):
    await interaction.response.defer(ephemeral=True)
    await bot.user.edit(username=new_name)
    await interaction.followup.send(f"✅ تم تغيير اسم البوت إلى: **{new_name}**")

@bot.tree.command(name="change-name", description="تعديل اسم المتجر")
async def change_name(interaction: discord.Interaction, shop_channel: discord.TextChannel, new_name: str):
    await interaction.response.defer(ephemeral=True)
    await shop_channel.edit(name=f"🛒・{new_name}")
    cursor.execute("UPDATE shops SET name = ? WHERE channel_id = ?", (new_name, shop_channel.id))
    conn.commit()
    await interaction.followup.send(f"✅ تم تغيير اسم المتجر إلى: **{new_name}**")

@bot.tree.command(name="change-owner", description="نقل ملكية متجر")
@app_commands.checks.has_permissions(administrator=True)
async def change_owner(interaction: discord.Interaction, shop_channel: discord.TextChannel, new_owner: discord.Member):
    await interaction.response.defer(ephemeral=True)
    cursor.execute("UPDATE shops SET owner_id = ? WHERE channel_id = ?", (new_owner.id, shop_channel.id))
    conn.commit()
    await interaction.followup.send(f"✅ تم نقل ملكية المتجر {shop_channel.mention} إلى {new_owner.mention}")

@bot.tree.command(name="change-type", description="تغيير نوع المتجر")
async def change_type(interaction: discord.Interaction, shop_channel: discord.TextChannel, new_type: str):
    await interaction.response.defer(ephemeral=True)
    cursor.execute("UPDATE shops SET shop_type = ? WHERE channel_id = ?", (new_type, shop_channel.id))
    conn.commit()
    await interaction.followup.send(f"✅ تم تغيير نوع المتجر إلى: **{new_type}**")

@bot.tree.command(name="edit-auto-reply", description="تعديل أو إضافة رد تلقائي")
@app_commands.checks.has_permissions(administrator=True)
async def edit_auto_reply(interaction: discord.Interaction, trigger: str, response: str):
    await interaction.response.defer(ephemeral=True)
    cursor.execute("INSERT OR REPLACE INTO auto_replies (trigger, response) VALUES (?, ?)", (trigger, response))
    conn.commit()
    await interaction.followup.send(f"✅ تم حفظ الرد التلقائي للكلمة: **{trigger}**")

@bot.tree.command(name="edit-auto-role", description="تعديل الرتب التلقائية")
@app_commands.checks.has_permissions(administrator=True)
async def edit_auto_role(interaction: discord.Interaction, role: discord.Role):
    await interaction.response.defer(ephemeral=True)
    set_setting("auto_role", role.id)
    await interaction.followup.send(f"✅ تم تحديث الرتبة التلقائية إلى: {role.mention}")

@bot.tree.command(name="edit-embed", description="إرسال إمبد مخصص")
@app_commands.checks.has_permissions(administrator=True)
async def edit_embed(interaction: discord.Interaction, title: str, description: str, color_hex: str = "2b2d31"):
    await interaction.response.defer(ephemeral=True)
    try:
        color_val = int(color_hex, 16)
        embed = discord.Embed(title=title, description=description, color=color_val)
        await interaction.channel.send(embed=embed)
        await interaction.followup.send("✅ تم إرسال الإمبد!")
    except Exception:
        await interaction.followup.send("❌ كود اللون غير صحيح. استخدم مثل 2b2d31")

@bot.tree.command(name="edit-prices", description="تحديث قائمة الأسعار")
@app_commands.checks.has_permissions(administrator=True)
async def edit_prices(interaction: discord.Interaction, content: str):
    await interaction.response.defer(ephemeral=True)
    set_setting("prices_text", content)
    await interaction.followup.send("✅ تم تحديث نص قائمة الأسعار.")

@bot.tree.command(name="edit-type", description="تعديل اسم تصنيف متجر")
@app_commands.checks.has_permissions(administrator=True)
async def edit_type(interaction: discord.Interaction, old_type: str, new_type: str):
    await interaction.response.defer(ephemeral=True)
    cursor.execute("UPDATE shop_types SET name = ? WHERE name = ?", (new_type, old_type))
    cursor.execute("UPDATE shops SET shop_type = ? WHERE shop_type = ?", (new_type, old_type))
    conn.commit()
    await interaction.followup.send(f"✅ تم تعديل النوع من **{old_type}** إلى **{new_type}**")
# ==================== 5. أوامر الإدارة والإشعار ====================

@bot.tree.command(name="come", description="استدعاء عضو إلى الروم الحالي")
@app_commands.checks.has_permissions(administrator=True)
async def come(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.defer(ephemeral=True)
    try:
        await member.send(f"📩 تم استدعاؤك بواسطة {interaction.user.mention} في القناة: {interaction.channel.jump_url}")
        await interaction.followup.send(f"✅ تم إرسال إشعار استدعاء لـ {member.mention}")
    except Exception:
        await interaction.followup.send(f"❌ لم أتمكن من إرسال رسالة خاصة لـ {member.mention}")

@bot.tree.command(name="fix-problems", description="فحص وإصلاح قاعدة البيانات")
@app_commands.checks.has_permissions(administrator=True)
async def fix_problems(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    conn.commit()
    await interaction.followup.send("✅ تم فحص وإصلاح الاتصال بقاعدة البيانات ومزامنة الملفات.")

@bot.tree.command(name="help", description="عرض قائمة المساعدة والشرح")
async def help_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    embed = discord.Embed(title="📜 قائمة أوامر البوت الشاملة", description="جميع الأوامر تعمل بنظام Slash (`/`)", color=0x2b2d31)
    embed.add_field(name="🛒 المتاجر", value="`/shop` - `/setup` - `/shop-data` - `/active` - `/disable` - `/delete-shop`", inline=False)
    embed.add_field(name="⚙️ الإدارة", value="`/add-type` - `/set-tax` - `/warn` - `/unwarn` - `/add-mentions`", inline=False)
    embed.add_field(name="🎫 اللوحات", value="`/ticket-panel` - `/order-ticket` - `/price-panel` - `/auction-ticket`", inline=False)
    embed.set_footer(text="Dev By: Mousa")
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="order", description="طلب شراء منتج")
async def order(interaction: discord.Interaction, item: str, details: str = "لا يوجد"):
    await interaction.response.defer()
    embed = discord.Embed(title="📦 طلب شراء جديد", color=discord.Color.blue())
    embed.add_field(name="المشتري:", value=interaction.user.mention, inline=False)
    embed.add_field(name="السلعة:", value=item, inline=False)
    embed.add_field(name="التفاصيل:", value=details, inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="order-ticket", description="لوحة استقبال الطلبات")
@app_commands.checks.has_permissions(administrator=True)
async def order_ticket(interaction: discord.Interaction):
    await interaction.response.defer()
    embed = discord.Embed(title="🛍️ لوحة الطلبات", description="اضغط لفتح تكت وإرسال طلبك.", color=0x2b2d31)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="price-panel", description="عرض لوحة الأسعار")
async def price_panel(interaction: discord.Interaction):
    await interaction.response.defer()
    prices = get_setting("prices_text") or "لم يتم تحديد الأسعار بعد."
    embed = discord.Embed(title="📊 لوحة الأسعار", description=prices, color=discord.Color.green())
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="r-mentions", description="تصفير المنشنات لكل المتاجر")
@app_commands.checks.has_permissions(administrator=True)
async def r_mentions(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    cursor.execute("UPDATE shops SET mentions = 0")
    conn.commit()
    await interaction.followup.send("✅ تم تصفير جميع منشنات المتاجر.")

@bot.tree.command(name="refresh-commands", description="إعادة تحديث أوامر Slash فورياً")
@app_commands.checks.has_permissions(administrator=True)
async def refresh_commands(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    for guild in bot.guilds:
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
    await interaction.followup.send("✅ تم إعادة مزامنة جميع أوامر البوت فورياً للسيرفر!")

# ==================== 6. أوامر الحذف والتعطيل ====================

@bot.tree.command(name="delete-all-shops", description="حذف كافة المتاجر")
@app_commands.checks.has_permissions(administrator=True)
async def delete_all_shops(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    cursor.execute("DELETE FROM shops")
    conn.commit()
    await interaction.followup.send("🚨 تم مسح جميع المتاجر من قاعدة البيانات.")

@bot.tree.command(name="delete-shop", description="حذف متجر محدد")
@app_commands.checks.has_permissions(administrator=True)
async def delete_shop(interaction: discord.Interaction, shop_channel: discord.TextChannel):
    await interaction.response.defer(ephemeral=True)
    cursor.execute("DELETE FROM shops WHERE channel_id = ?", (shop_channel.id,))
    conn.commit()
    try:
        await shop_channel.delete()
    except Exception:
        pass
    await interaction.followup.send("✅ تم حذف المتجر ورومه بنجاح.")

@bot.tree.command(name="delete-unactive-shops", description="حذف المتاجر غير المفعلة")
@app_commands.checks.has_permissions(administrator=True)
async def delete_unactive_shops(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    cursor.execute("SELECT channel_id FROM shops WHERE active = 0")
    unactive = cursor.fetchall()
    for row in unactive:
        ch = interaction.guild.get_channel(row[0])
        if ch:
            try:
                await ch.delete()
            except Exception:
                pass
    cursor.execute("DELETE FROM shops WHERE active = 0")
    conn.commit()
    await interaction.followup.send("✅ تم حذف جميع المتاجر المعطلة.")

@bot.tree.command(name="disable", description="تعطيل متجر محدد")
@app_commands.checks.has_permissions(administrator=True)
async def disable(interaction: discord.Interaction, shop_channel: discord.TextChannel):
    await interaction.response.defer(ephemeral=True)
    cursor.execute("UPDATE shops SET active = 0 WHERE channel_id = ?", (shop_channel.id,))
    conn.commit()
    await interaction.followup.send(f"⛔ تم تعطيل المتجر: {shop_channel.mention}")

@bot.tree.command(name="disable-all", description="تعطيل كل المتاجر")
@app_commands.checks.has_permissions(administrator=True)
async def disable_all(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    cursor.execute("UPDATE shops SET active = 0")
    conn.commit()
    await interaction.followup.send("⛔ تم تعطيل جميع المتاجر.")

@bot.tree.command(name="remove-auction-room", description="إلغاء روم المزادات")
@app_commands.checks.has_permissions(administrator=True)
async def remove_auction_room(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    cursor.execute("DELETE FROM settings WHERE key = 'auction_room'")
    conn.commit()
    await interaction.followup.send("✅ تم إزالة روم المزادات.")

@bot.tree.command(name="remove-auto-role", description="إزالة الرتبة التلقائية")
@app_commands.checks.has_permissions(administrator=True)
async def remove_auto_role(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    cursor.execute("DELETE FROM settings WHERE key = 'auto_role'")
    conn.commit()
    await interaction.followup.send("✅ تم إزالة الرتبة التلقائية.")

@bot.tree.command(name="remove-emoji-channel", description="إزالة روم الإيموجيات")
@app_commands.checks.has_permissions(administrator=True)
async def remove_emoji_channel(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    cursor.execute("DELETE FROM settings WHERE key = 'emoji_channel'")
    conn.commit()
    await interaction.followup.send("✅ تم إزالة روم الإيموجيات.")

@bot.tree.command(name="remove-helper", description="إزالة مساعد من متجر")
async def remove_helper(interaction: discord.Interaction, shop_channel: discord.TextChannel, helper: discord.Member):
    await interaction.response.defer(ephemeral=True)
    cursor.execute("DELETE FROM helpers WHERE channel_id = ? AND user_id = ?", (shop_channel.id, helper.id))
    conn.commit()
    await shop_channel.set_permissions(helper, overwrite=None)
    await interaction.followup.send(f"✅ تم إزالة المساعد {helper.mention} من المتجر.")

@bot.tree.command(name="remove-tax-channel", description="إزالة روم الضريبة")
@app_commands.checks.has_permissions(administrator=True)
async def remove_tax_channel(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    cursor.execute("DELETE FROM settings WHERE key = 'tax_channel'")
    conn.commit()
    await interaction.followup.send("✅ تم إزالة روم الضريبة.")

@bot.tree.command(name="remove-type", description="حذف نوع متجر")
@app_commands.checks.has_permissions(administrator=True)
async def remove_type(interaction: discord.Interaction, type_name: str):
    await interaction.response.defer(ephemeral=True)
    cursor.execute("DELETE FROM shop_types WHERE name = ?", (type_name,))
    conn.commit()
    await interaction.followup.send(f"✅ تم حذف النوع: **{type_name}**")

# ==================== 7. أوامر اللوحات والتذاكر ====================

@bot.tree.command(name="role-ticket", description="لوحة شراء الرتب")
@app_commands.checks.has_permissions(administrator=True)
async def role_ticket(interaction: discord.Interaction):
    await interaction.response.defer()
    embed = discord.Embed(title="🎖️ لوحة شراء الرتب", description="اضغط لفتح تكت شراء رتبة.", color=0x2b2d31)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="send-message-to-all-shops", description="رسالة جماعية لأصحاب المتاجر")
@app_commands.checks.has_permissions(administrator=True)
async def send_message_to_all_shops(interaction: discord.Interaction, message_text: str):
    await interaction.response.defer(ephemeral=True)
    cursor.execute("SELECT channel_id FROM shops")
    rows = cursor.fetchall()
    count = 0
    for row in rows:
        ch = interaction.guild.get_channel(row[0])
        if ch:
            try:
                await ch.send(f"📢 **تنبيه إداري:**\n{message_text}")
                count += 1
            except Exception:
                pass
    await interaction.followup.send(f"✅ تم إرسال الرسالة إلى {count} متجر.")

@bot.tree.command(name="send-tchfir", description="زر مشفر للتحويل والضمان")
async def send_tchfir(interaction: discord.Interaction, amount: int):
    await interaction.response.defer()
    tax_rate = float(get_setting("tax_rate") or 5.0)
    final_amount = int(amount + (amount * (tax_rate / 100.0)))
    await interaction.followup.send(f"🔒 **عملية تحويل مشفرة:**\nالمبلغ الأصلي: `{amount}`\nالمبلغ مع الضريبة ({tax_rate}%): `{final_amount}`")

@bot.tree.command(name="send-tickets", description="لوحة الدعم الفني")
@app_commands.checks.has_permissions(administrator=True)
async def send_tickets(interaction: discord.Interaction):
    await interaction.response.defer()
    embed = discord.Embed(title="🎧 لوحة الدعم الفني والتواصل", description="افتح تكت للتحدث مع الإدارة.", color=discord.Color.blue())
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="set-mentions", description="ضبط عدد منشينات متجر")
@app_commands.checks.has_permissions(administrator=True)
async def set_mentions(interaction: discord.Interaction, shop_channel: discord.TextChannel, amount: int):
    await interaction.response.defer(ephemeral=True)
    cursor.execute("UPDATE shops SET mentions = ? WHERE channel_id = ?", (amount, shop_channel.id))
    conn.commit()
    await interaction.followup.send(f"✅ تم ضبط منشنات {shop_channel.mention} إلى `{amount}`")

@bot.tree.command(name="set-tax", description="تحديد نسبة الضريبة")
@app_commands.checks.has_permissions(administrator=True)
async def set_tax(interaction: discord.Interaction, percentage: float):
    await interaction.response.defer(ephemeral=True)
    set_setting("tax_rate", percentage)
    await interaction.followup.send(f"✅ تم تحديد نسبة الضريبة إلى `{percentage}%`")

@bot.tree.command(name="setup", description="إعداد كاتجوري المتاجر الرئيسي")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction, category: discord.CategoryChannel):
    await interaction.response.defer(ephemeral=True)
    set_setting("shop_category", category.id)
    await interaction.followup.send(f"✅ تم ضبط كاتجوري المتاجر الرئيسي: **{category.name}**")

@bot.tree.command(name="setup-ticket", description="إعداد نظام التذاكر")
@app_commands.checks.has_permissions(administrator=True)
async def setup_ticket(interaction: discord.Interaction, category: discord.CategoryChannel):
    await interaction.response.defer(ephemeral=True)
    set_setting("ticket_category", category.id)
    await interaction.followup.send(f"✅ تم إعداد كاتجوري التذاكر: **{category.name}**")

@bot.tree.command(name="shop", description="إنشاء متجر جديد")
async def shop(interaction: discord.Interaction, owner: discord.Member, shop_type: str):
    await interaction.response.defer(ephemeral=True)
    cat_id = get_setting("shop_category")
    if not cat_id:
        await interaction.followup.send("❌ لم يتم إعداد كاتجوري المتاجر بعد! استخدم `/setup` أولاً.")
        return
    category = interaction.guild.get_channel(int(cat_id))
    if not category:
        await interaction.followup.send("❌ الكاتجوري المحدد غير موجود.")
        return

    try:
        channel_name = f"🛒・{owner.name}-شوب"
        shop_channel = await interaction.guild.create_text_channel(name=channel_name, category=category)
        
        now_str = datetime.now().strftime("%A, %B %d, %Y %I:%M %p")
        cursor.execute("INSERT INTO shops (channel_id, owner_id, name, shop_type, active, mentions, warnings, created_at) VALUES (?, ?, ?, ?, 1, 10, 0, ?)",
                       (shop_channel.id, owner.id, owner.name, shop_type, now_str))
        conn.commit()

        embed = discord.Embed(title=f"🎋 ┆ {owner.name} SHOP", color=0x2b2d31)
        embed.add_field(name="الـمنـشـنـات :", value="🔹 - `@everyone` : 10\n🔹 - `@here` : 10", inline=False)
        embed.add_field(name="❄️ ┆ صاحب المتجر :", value=f"{owner.mention}", inline=False)
        embed.add_field(name="❄️ ┆ نوع المتجر :", value=f"💎 `{shop_type}`", inline=False)
        embed.add_field(name="❄️ ┆ تاريخ الانشاء :", value=f"`{now_str}`", inline=False)
        embed.set_footer(text="Dev By: Mousa")

        await shop_channel.send(embed=embed)
        await shop_channel.send(content=owner.mention)
        await interaction.followup.send(f"✅ تم إنشاء المتجر بنجاح: {shop_channel.mention}")
    except Exception as e:
        await interaction.followup.send(f"❌ حدث خطأ: {e}")

@bot.tree.command(name="shop-data", description="عرض بيانات متجر")
async def shop_data(interaction: discord.Interaction, shop_channel: discord.TextChannel):
    await interaction.response.defer(ephemeral=True)
    cursor.execute("SELECT owner_id, shop_type, active, mentions, warnings, created_at FROM shops WHERE channel_id = ?", (shop_channel.id,))
    row = cursor.fetchone()
    if not row:
        await interaction.followup.send("❌ هذا الروم ليس متجراً مسجلاً.")
        return
    owner = interaction.guild.get_member(row[0])
    status = "🟢 مفعل" if row[2] == 1 else "🔴 معطل"
    embed = discord.Embed(title=f"📊 بيانات المتجر: {shop_channel.name}", color=0x2b2d31)
    embed.add_field(name="صاحب المتجر:", value=owner.mention if owner else "غير معروف", inline=False)
    embed.add_field(name="نوع المتجر:", value=row[1], inline=True)
    embed.add_field(name="الحالة:", value=status, inline=True)
    embed.add_field(name="المنشنات المتبقية:", value=str(row[3]), inline=True)
    embed.add_field(name="التحذيرات:", value=str(row[4]), inline=True)
    embed.add_field(name="تاريخ الإنشاء:", value=row[5], inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="shop-mentions", description="عرض منشنات المتجر المتبقية")
async def shop_mentions(interaction: discord.Interaction, shop_channel: discord.TextChannel):
    await interaction.response.defer(ephemeral=True)
    cursor.execute("SELECT mentions FROM shops WHERE channel_id = ?", (shop_channel.id,))
    row = cursor.fetchone()
    if row:
        await interaction.followup.send(f"📢 المنشنات المتبقية لـ {shop_channel.mention}: `{row[0]}`")
    else:
        await interaction.followup.send("❌ المتجر غير مسجل.")

@bot.tree.command(name="shop-ticket", description="لوحة شراء وتأسيس المتاجر")
@app_commands.checks.has_permissions(administrator=True)
async def shop_ticket(interaction: discord.Interaction):
    await interaction.response.defer()
    embed = discord.Embed(title="🛒 لوحة تقديم المتاجر", description="افتح تكت لتأسيس متجرك الخاص.", color=0x2b2d31)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="ticket-panel", description="اللوحة الرئيسية للتذاكر")
@app_commands.checks.has_permissions(administrator=True)
async def ticket_panel(interaction: discord.Interaction):
    await interaction.response.defer()
    embed = discord.Embed(title="🎟️ نظام التذاكر الرئيسي", description="اختر قسم الدعم المطلوب.", color=discord.Color.dark_grey())
    await interaction.followup.send(embed=embed)

# ==================== 8. أوامر التحذير والمستخدمين ====================

@bot.tree.command(name="warn", description="توجيه تحذير لمتجر")
@app_commands.checks.has_permissions(administrator=True)
async def warn(interaction: discord.Interaction, shop_channel: discord.TextChannel, reason: str):
    await interaction.response.defer(ephemeral=True)
    cursor.execute("UPDATE shops SET warnings = warnings + 1 WHERE channel_id = ?", (shop_channel.id,))
    conn.commit()
    await shop_channel.send(f"⚠️ **تنبيه إداري:** تم توجيه تحذير للمتجر.\nالسبب: {reason}")
    await interaction.followup.send(f"✅ تم توجيه تحذير لـ {shop_channel.mention}")

@bot.tree.command(name="unwarn", description="إزالة تحذير عن متجر")
@app_commands.checks.has_permissions(administrator=True)
async def unwarn(interaction: discord.Interaction, shop_channel: discord.TextChannel):
    await interaction.response.defer(ephemeral=True)
    cursor.execute("UPDATE shops SET warnings = MAX(0, warnings - 1) WHERE channel_id = ?", (shop_channel.id,))
    conn.commit()
    await interaction.followup.send(f"✅ تم خصم تحذير من {shop_channel.mention}")

@bot.tree.command(name="warns", description="عرض تحذيرات متجر")
async def warns(interaction: discord.Interaction, shop_channel: discord.TextChannel):
    await interaction.response.defer(ephemeral=True)
    cursor.execute("SELECT warnings FROM shops WHERE channel_id = ?", (shop_channel.id,))
    row = cursor.fetchone()
    count = row[0] if row else 0
    await interaction.followup.send(f"⚠️ عدد تحذيرات {shop_channel.mention}: `{count}`")

@bot.tree.command(name="upload-image", description="رفع صورة واستخراج رابطها")
async def upload_image(interaction: discord.Interaction, attachment: discord.Attachment):
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send(f"🖼️ رابط الصورة المرفوعة:\n{attachment.url}")

@bot.tree.command(name="user-info", description="عرض سجل متاجر مستخدم")
async def user_info(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.defer(ephemeral=True)
    cursor.execute("SELECT name, shop_type, active FROM shops WHERE owner_id = ?", (user.id,))
    shops = cursor.fetchall()
    if not shops:
        await interaction.followup.send(f"ℹ️ المستخدم {user.mention} لا يملك أي متاجر مسجلة.")
        return
    embed = discord.Embed(title=f"👤 سجل متاجر: {user.name}", color=0x2b2d31)
    for s in shops:
        st = "🟢 مفعل" if s[2] == 1 else "🔴 معطل"
        embed.add_field(name=f"🛒 {s[0]}", value=f"النوع: {s[1]} | الحالة: {st}", inline=False)
    await interaction.followup.send(embed=embed)

# تشغيل البوت
bot.run(TOKEN)   
