# Rnai-CLI

AI agent CLI ของระบบ Rnai.io — คุยกับ rnai-llm, เทียบกับโมเดลฟรีอื่น, และสั่งงาน agent ที่ค้นเว็บ/จัดการไฟล์/รันคำสั่ง/เรียก Rnai.io skills ได้ (Phase 1 ของแผน Rnai-CLI → Worker → Cowork Webapp)

## ติดตั้ง

```bash
cd Rnai-CLI
pip3 install -e .
```

## ตั้งค่า key (ครั้งเดียว)

```bash
rnai config set GROQ_API_KEY gsk_xxx      # ฟรีที่ console.groq.com (สมองหลัก agent)
rnai config set GEMINI_API_KEY xxx        # aistudio.google.com (สำรอง/เทียบ)
rnai config set TAVILY_API_KEY tvly_xxx   # tavily.com (web search ฟรี 1,000/เดือน)
rnai config set RNAI_IO_API_KEY rnai_sk_x # จากหน้าโปรไฟล์ Rnai.io (เรียก skills)
rnai config list
```

## ใช้งาน

```bash
rnai chat "ผ่อน 0% 10 เดือน กับจ่ายสดลด 5% เลือกอันไหนดี"   # คุยกับ rnai-llm
rnai chat "..." --think                                      # เห็น reasoning
rnai chat "..." -m groq                                      # สลับโมเดล
rnai status                                                  # เช็ค Modal/Vercel/keys
rnai wake                                                    # ปลุกโมเดลก่อนเดโม่
rnai compare "อธิบาย LoRA ให้คนทั่วไปฟัง"                    # เทียบ 3 โมเดล + ความเร็ว
rnai agent "ค้นราคา MacBook Air ล่าสุดแล้วสรุปเป็นไฟล์ macbook.md"
```

## Agent (hybrid)

- **Planner** (Groq/Gemini): วางแผน + เรียก tools — `web_search`, `read_file`, `write_file`, `run_command`, `rnai_skill`
- **Voice** (rnai-llm): เรียบเรียงคำตอบสุดท้ายเป็นบุคลิก Rnai (`--voice none` เพื่อปิด)
- ทุก action ที่แก้ไขระบบ (เขียนไฟล์/รันคำสั่ง) **ถามยืนยันก่อนเสมอ**

## หมายเหตุ

- ข้อความแรกหลังโมเดลหลับ ~10 นาที จะช้า (cold start ~2 นาที) — ใช้ `rnai wake` ก่อน
- system prompt ของ rnai-llm ฝังไว้ตรงกับตอนเทรนแล้ว อย่าแก้ใน config ถ้าไม่เปลี่ยนรอบเทรน
- อย่า commit `~/.rnai/config.json` — key อยู่นอก repo อยู่แล้ว
