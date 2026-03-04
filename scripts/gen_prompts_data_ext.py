"""Extended clip definitions for Sosed series — filling gaps to reach ~300 clips."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from gen_prompts import CHARS, LOCS, STYLE

ST = STYLE
A = CHARS["amin"]["path"]
Y = CHARS["aya"]["path"]
T = CHARS["tako"]["path"]
K = CHARS["karim"]["path"]
P = CHARS["papa"]["path"]
M = CHARS["mama"]["path"]
J = CHARS["jamil"]["path"]
SB = CHARS["simba"]["path"]
L = lambda key: LOCS[key]

def raw(clip_id, scene_id, desc, ingredients, fa, fb, la, lb):
    return {
        "clip_id": clip_id, "scene_id": scene_id,
        "scene_description_ru": desc,
        "nano_banana_ingredients": ingredients,
        "nano_banana_prompt_first": fa, "nano_banana_prompt_first_b": fb,
        "nano_banana_prompt_mid": None, "nano_banana_prompt_mid_b": None,
        "nano_banana_prompt_last": la, "nano_banana_prompt_last_b": lb,
        "veo_prompt": None, "veo_prompt_b": None,
        "veo_mode": "frames", "veo_variant_count": 4
    }

EXT_CLIPS = []

# ============================================================
# SCENE 1 — ORIGINAL clips (A-O) — восстановление
# ============================================================

EXT_CLIPS.append(raw("S01_A", "S01",
    "Установочный кадр: пыльная улица, золотой час, длинные тени.",
    [L("house_front")],
    f"Wide establishing shot of a quiet residential street at golden hour. Long shadows stretch across the dusty ground. Low sun paints everything warm orange-gold. Use Image 1 as the exact background location. Wide shot, low angle. Golden hour, warm saturated light. {ST}",
    f"A peaceful dusty street bathed in late afternoon sunlight. Long dramatic shadows from houses and fences. Warm golden atmosphere, not a soul in sight. Use Image 1 as the exact background location. Ultra-wide shot, eye-level. Golden hour, rich warm tones. {ST}",
    f"The same quiet street as golden light deepens. Shadows grow longer, the warmth intensifies. A feeling of an ordinary evening about to become extraordinary. Use Image 1 as the exact background location. Wide shot, slightly low angle. Deep golden hour, amber tones. {ST}",
    f"A residential street glowing in sunset light. Dust particles visible in the warm air. Deep orange shadows paint the ground. Calm, peaceful, expectant. Use Image 1 as the exact background location. Wide establishing shot, eye-level. Late golden hour, warm cinematic light. {ST}",
))

EXT_CLIPS.append(raw("S01_B", "S01",
    "Амин сидит на ступеньках, читает книгу со схемой двигателя. Ая рядом рисует в блокноте.",
    [A, Y, L("house_front")],
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, sitting on porch steps reading a thick book with an engine diagram on the cover. The exact character in a pink dress and dark navy striped hijab from Image 2, sitting on the porch railing nearby, drawing in a sketchbook with a pencil between her teeth. Use Image 3 as the exact background location. Medium shot, eye-level. Golden hour, warm light. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, sitting on stone porch steps absorbed in a thick technical book. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, perched on the porch railing beside him sketching in a notebook, pencil held lightly between her teeth. Use Image 3 as the exact background location. Medium-wide shot, slightly low angle. Late afternoon golden light. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, looking up from his book with curiosity. The exact character in a pink dress and dark navy striped hijab from Image 2, pausing her drawing, looking in the same direction. Use Image 3 as the exact background location. Medium shot, eye-level. Golden hour, warm light. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, lowering his book and turning his head. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, glancing up from her sketchbook with interest. Use Image 3 as the exact background location. Medium shot, slight low angle. Late afternoon golden light. {ST}",
))

EXT_CLIPS.append(raw("S01_C", "S01",
    "Тако бросает мяч о стену, считает отскоки. Мяч летит криво через забор.",
    [T, L("house_front")],
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, bouncing a ball against a wall in the yard, counting each bounce with concentration. The ball ricochets at a bad angle and sails over the wooden fence. Use Image 2 as the exact background location. Medium shot, eye-level. Golden hour, warm light. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, throwing a ball at a wall and catching it repeatedly in a courtyard. Suddenly the ball flies off at an angle, arcing over the fence and disappearing. Use Image 2 as the exact background location. Medium-wide shot, slightly low angle. Late afternoon golden light. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, frozen mid-motion with hands still raised, staring at the fence where the ball just disappeared. Comedic shock on his face. Use Image 2 as the exact background location. Medium shot, eye-level. Golden hour, warm light. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, standing with arms still outstretched, mouth open in surprise, looking at the spot where the ball flew over the fence. Use Image 2 as the exact background location. Medium close-up, eye-level. Golden hour, warm sidelight. {ST}",
))

EXT_CLIPS.append(raw("S01_D", "S01",
    "Симба лежит у ворот в тени. Поднимает голову. Зевает. Опускает морду.",
    [SB, L("house_front")],
    f"The exact animal from Image 1, preserving identical facial features and proportions, lying lazily by an iron gate in the shade. The dog lifts its head, looks at something off-screen, yawns widely showing teeth, then drops its muzzle back onto its paws. Use Image 2 as the exact background location. Medium shot, low angle. Golden hour, warm light. {ST}",
    f"The exact animal from Image 1, preserving identical facial features and proportions, resting in the shadow of a gate. It raises its head sleepily, gives a long exaggerated yawn, then settles back down with zero interest. Use Image 2 as the exact background location. Close-up, ground level. Late afternoon, dappled shade. {ST}",
    f"The exact animal from Image 1, preserving identical facial features and proportions, lying by the gate, eyes half-closed. The dog is unbothered, utterly relaxed. One ear twitches but otherwise no movement. Use Image 2 as the exact background location. Medium close-up, low angle. Golden hour, warm shadow. {ST}",
    f"The exact animal from Image 1, preserving identical facial features and proportions, curled up by a metal gate, dozing peacefully in the shade. Not a care in the world. Use Image 2 as the exact background location. Close-up, low angle. Warm golden light, deep shadows. {ST}",
))

EXT_CLIPS.append(raw("S01_E", "S01",
    "Звук мотора. Все трое оборачиваются — Амин, Ая, Тако.",
    [A, Y, T, L("house_front")],
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, turning sharply toward an off-screen sound. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, looking up from her sketchbook in the same direction. Then, the exact character in a red-and-white striped shirt and red cap from Image 3, already at the fence, peering curiously. Use Image 4 as the exact background location. Medium-wide shot, eye-level. Golden hour, warm light. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, raising his head from a book with alert curiosity. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, pausing mid-drawing, turning to look. Then, the exact character in a red-and-white striped shirt and red cap from Image 3, spinning around toward the sound. All three looking in the same direction. Use Image 4 as the exact background location. Medium shot, eye-level. Golden hour, warm tones. {ST}",
    f"All three characters frozen mid-action, staring toward the source of a sound. The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, standing with the book at his side. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, eyes wide with curiosity. Then, the exact character in a red-and-white striped shirt and red cap from Image 3, gripping the fence and leaning forward. Use Image 4 as the exact background location. Medium shot, slight low angle. Golden hour, dramatic sidelight. {ST}",
    f"Three children watching something approach. The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, alert and focused. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, curious but composed. Then, the exact character in a red-and-white striped shirt and red cap from Image 3, bouncing with excitement at the fence. Use Image 4 as the exact background location. Medium-wide shot, eye-level. Deep golden hour light. {ST}",
))

EXT_CLIPS.append(raw("S01_F", "S01",
    "Тёмно-зелёный потёртый фургон подъезжает к пустому соседнему дому.",
    [L("jamil_house_front")],
    f"A dark green van pulling up to an old empty house. The van is scratched and road-worn, with faded stickers on its sides. It comes to a stop in front of the house. Dust settles around the wheels. Use Image 1 as the exact background location. Wide shot, eye-level. Golden hour, warm light. {ST}",
    f"A weathered dark-green cargo van arriving at a modest old house that has stood empty. The van stops, engine dies. Dust drifts in the warm air. Faded decals visible on the van panels. Use Image 1 as the exact background location. Medium-wide shot, slightly low angle. Late afternoon sunlight. {ST}",
    f"The dark green van now parked in front of the old house. Engine off. Silence. The van door is about to open. Dust motes float in the golden light. Use Image 1 as the exact background location. Medium shot, eye-level. Golden hour, warm cinematic tones. {ST}",
    f"A still moment — the dark green van sits in front of the empty house. Warm light bathes the scene. The van door handle catches the sunlight. Anticipation hangs in the air. Use Image 1 as the exact background location. Medium-wide shot, slight low angle. Deep golden hour light. {ST}",
))

EXT_CLIPS.append(raw("S01_G", "S01",
    "Джамиль выходит из фургона. Светлая рубашка, закатанные рукава, седая борода, очки на лбу.",
    [J, L("jamil_house_front")],
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, stepping out of a dark green van. He stands for a moment, looking at the old house before him. Calm, unhurried demeanor. Use Image 2 as the exact background location. Medium shot, eye-level. Golden hour, warm light. {ST}",
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, emerging from the driver side of a van. He straightens up slowly, adjusting glasses on his forehead. Gazing at the house with quiet recognition. Use Image 2 as the exact background location. Medium close-up, slight low angle. Late afternoon golden light. {ST}",
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, standing in front of the old house. He nods to himself — a small, private gesture of decision. Then turns toward the rear of the van. Use Image 2 as the exact background location. Medium shot, eye-level. Golden hour, warm sidelight. {ST}",
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, walking purposefully toward the back of his van. He reaches for the rear door handles. Determined but gentle expression. Use Image 2 as the exact background location. Medium shot, over-shoulder angle. Golden hour, warm backlight. {ST}",
))

EXT_CLIPS.append(raw("S01_H", "S01",
    "Джамиль открывает заднюю дверь фургона — внутри ящики с маркировкой на разных языках.",
    [J, L("jamil_house_front")],
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, pulling open the rear doors of a dark green van. Inside — tightly packed wooden crates, cardboard boxes, burlap-wrapped bundles. Markings in Arabic, English, and other scripts visible. Use Image 2 as the exact background location. Medium shot, over-shoulder. Golden hour, warm light illuminating the cargo. {ST}",
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, standing at the open rear of his van. Rows of wooden and cardboard crates fill the interior. Foreign labels and shipping marks visible. One crate shows hand-written numbers. Use Image 2 as the exact background location. Medium-wide shot, eye-level. Late afternoon light streaming into the van. {ST}",
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, lifting a heavy wooden crate from the van. Muscles straining slightly under the rolled-up sleeves. Determined expression. Use Image 2 as the exact background location. Medium shot, eye-level. Golden hour, warm light. {ST}",
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, carrying a wooden crate toward the front door of the house. Walking slowly, carefully. The crate looks heavy. Use Image 2 as the exact background location. Medium-wide shot, slight low angle. Deep golden hour, long shadows. {ST}",
))

EXT_CLIPS.append(raw("S01_I", "S01",
    "Симба встаёт, уши торчком, тихое настороженное рычание — новый запах.",
    [SB, L("house_front")],
    f"The exact animal from Image 1, preserving identical facial features and proportions, standing alert by a fence. Ears fully erect, nose working, body tense. A low cautious growl — not aggressive, but watchful. Sensing a new presence. Use Image 2 as the exact background location. Medium close-up, low angle. Golden hour, warm dramatic light. {ST}",
    f"The exact animal from Image 1, preserving identical facial features and proportions, on its feet now, ears pointed forward, sniffing the air intently. The dog's posture is alert and protective — guarding its territory. A quiet rumble in its chest. Use Image 2 as the exact background location. Medium shot, ground level. Late afternoon, warm sidelight. {ST}",
    f"The exact animal from Image 1, preserving identical facial features and proportions, standing rigid, ears up, staring at something off-screen. Every muscle alert. Nose twitching. Tail still. Use Image 2 as the exact background location. Close-up, low angle. Golden hour, dramatic light. {ST}",
    f"The exact animal from Image 1, preserving identical facial features and proportions, settling into a watchful sit by the fence, eyes locked on the neighboring house. Still alert but now patient. Guarding. Use Image 2 as the exact background location. Medium shot, low angle. Warm golden light. {ST}",
))

EXT_CLIPS.append(raw("S01_J", "S01",
    "Тако перегибается через забор — 'Ас-саляму алейкум!'",
    [T, L("fence")],
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, leaning over a wooden fence, gripping the top board with both hands. Mouth open in a cheerful greeting, eyes bright and curious. Use Image 2 as the exact background location. Medium close-up, slight low angle from the other side of the fence. Golden hour, warm backlight. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, hanging over the top of a wooden fence, chin almost resting on it. A huge friendly grin. Waving with one hand while gripping the fence with the other. Use Image 2 as the exact background location. Medium shot, eye-level. Late afternoon, warm golden light. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, still perched on the fence, beaming. Confident, social, zero shyness. Use Image 2 as the exact background location. Medium close-up, slight low angle. Golden hour, warm rim light on the cap. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, at the fence, eyes wide, talking animatedly. Gesturing with one hand, the other clutching the fence top. Excited energy. Use Image 2 as the exact background location. Close-up, eye-level. Warm golden light. {ST}",
))

EXT_CLIPS.append(raw("S01_K", "S01",
    "Джамиль с ящиком в руках. Оценивающий взгляд на Тако, потом тёплая усталая улыбка.",
    [J, T, L("fence")],
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, holding a wooden crate, looking at a boy on the other side of a fence. His expression shifts from a brief assessing look to a warm, tired smile. Then, the exact character in a red-and-white striped shirt and red cap from Image 2, leaning on the fence beaming up at him. Use Image 3 as the exact background location. Medium shot, eye-level. Golden hour, warm light. {ST}",
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, paused with a heavy crate in his arms. A gentle, slightly weary smile on his face as he looks at a child on the fence. Then, the exact character in a red-and-white striped shirt and red cap from Image 2, grinning and full of energy. Use Image 3 as the exact background location. Two-shot, eye-level. Late afternoon golden light. {ST}",
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, smiling warmly at the boy. A genuine, human moment. Then, the exact character in a red-and-white striped shirt and red cap from Image 2, chatting enthusiastically from his perch on the fence. Use Image 3 as the exact background location. Medium shot, eye-level. Golden hour, warm cinematic light. {ST}",
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, shaking his head gently with a smile, refusing help. He turns and walks toward the house carrying the crate. Then, the exact character in a red-and-white striped shirt and red cap from Image 2, watching him go with wide curious eyes. Use Image 3 as the exact background location. Medium-wide shot, eye-level. Deep golden hour. {ST}",
))

EXT_CLIPS.append(raw("S01_L", "S01",
    "Тако оборачивается к Амину и Ае — 'У него на ящике координаты!'",
    [T, A, Y, L("house_front")],
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, turning back from the fence with excited wide eyes, whispering urgently to two other kids. Then, the exact character in a grey hoodie from Image 2, listening with raised eyebrows. Then, the exact character in a pink dress and dark navy striped hijab from Image 3, looking skeptical but intrigued. Use Image 4 as the exact background location. Medium shot, eye-level. Golden hour, warm light. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, bouncing with excitement, gesturing back toward the neighbor's house. Whispering conspiratorially. Then, the exact character in a grey hoodie from Image 2, closing his book with interest. Then, the exact character in a pink dress and dark navy striped hijab from Image 3, tilting her head thoughtfully. Use Image 4 as the exact background location. Medium group shot, eye-level. Late afternoon golden light. {ST}",
    f"Three children huddled together. The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, dramatically whispering to the others. Then, the exact character in a grey hoodie from Image 2, leaning forward with curiosity. Then, the exact character in a pink dress and dark navy striped hijab from Image 3, arms crossed but eyes sharp. Use Image 4 as the exact background location. Medium close-up, eye-level. Golden hour, intimate warm light. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, spreading his hands dramatically while telling something exciting. Then, the exact character in a grey hoodie from Image 2, exchanging a glance with the girl. Then, the exact character in a pink dress and dark navy striped hijab from Image 3, raising one eyebrow. Use Image 4 as the exact background location. Medium shot, slight low angle. Deep golden hour. {ST}",
))

EXT_CLIPS.append(raw("S01_M", "S01",
    "Джамиль возвращается за ящиком, замечает что все трое смотрят. Представляется.",
    [J, A, L("fence")],
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, standing with a crate in his hands, looking at a boy across a fence. A moment of mutual assessment. Use Image 3 as the exact background location. Medium shot, eye-level. Golden hour, warm light. Then, the exact character in a grey hoodie from Image 2, introducing himself politely. {ST}",
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, pausing by his van, noticing three children watching him. He tilts his head slightly — curious, not annoyed. Then, the exact character in a grey hoodie from Image 2, stepping forward to speak. Use Image 3 as the exact background location. Medium-wide shot, eye-level. Late afternoon golden light. {ST}",
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, nodding politely to a boy. Dignified, measured. Then, the exact character in a grey hoodie from Image 2, standing respectfully. Use Image 3 as the exact background location. Two-shot, eye-level. Golden hour, warm cinematic light. {ST}",
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, picking up another crate and turning toward his house. The conversation is over. Polite but firm. Then, the exact character in a grey hoodie from Image 2, watching him go thoughtfully. Use Image 3 as the exact background location. Medium shot, eye-level. Deep golden hour. {ST}",
))

EXT_CLIPS.append(raw("S01_N", "S01",
    "Дверь дома Джамиля закрывается плотнее. Щелчок.",
    [L("jamil_house_front")],
    f"Close-up of an old wooden door closing firmly. A hand pulls it shut. The latch clicks into place. Decisive. Final. Use Image 1 as the exact background location. Close-up, eye-level. Golden hour, warm light fading on the wood. {ST}",
    f"An old wooden door being pulled closed from inside. The gap narrows, then — click. Shut. A moment of silence. Use Image 1 as the exact background location. Close-up, slight angle. Late afternoon, last warm light on the doorframe. {ST}",
    f"The closed door of an old house. Just shut. The wood still vibrates from the closing. Silence settles. Use Image 1 as the exact background location. Medium shot, eye-level. Deep golden hour, shadows growing. {ST}",
    f"The front of an old house — door firmly closed. No light from inside. A quiet finality to the scene. Use Image 1 as the exact background location. Medium-wide shot, eye-level. Golden hour, shadows lengthening. {ST}",
))

EXT_CLIPS.append(raw("S01_O", "S01",
    "Симба подходит к забору Джамиля. Обнюхивает столб. Садится. Смотрит на дверь. Не уходит.",
    [SB, L("jamil_house_front")],
    f"The exact animal from Image 1, preserving identical facial features and proportions, walking to a fence post near a house. The dog sniffs the post carefully, then sits down facing the closed door. Alert, patient, watching. Not leaving. Use Image 2 as the exact background location. Medium shot, low angle. Golden hour, warm light. {ST}",
    f"The exact animal from Image 1, preserving identical facial features and proportions, settled at the base of a fence post, nose still working. The dog stares at a closed door with quiet intensity. Ears forward, tail still. A self-appointed guard. Use Image 2 as the exact background location. Medium close-up, ground level. Late afternoon, long shadows. {ST}",
    f"The exact animal from Image 1, preserving identical facial features and proportions, sitting motionless by a fence, watching a closed door. Patient and unwavering. The last golden light of the day paints the scene. Use Image 2 as the exact background location. Wide shot, low angle. Deep golden hour, cinematic. {ST}",
    f"The exact animal from Image 1, preserving identical facial features and proportions, silhouetted against fading golden light, sitting vigil by a fence. Watching. Waiting. Use Image 2 as the exact background location. Wide shot, low angle. Sunset, dramatic warm backlight. {ST}",
))

# ============================================================
# SCENE 2 — ORIGINAL clips (A-C) — восстановление
# ============================================================

EXT_CLIPS.append(raw("S02_A", "S02",
    "Гараж-мастерская утром. Амин, Ая, Карим за столом, Тако на перевёрнутом ведре.",
    [A, Y, K, L("garage")],
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, sitting at a workbench in a garage, leaning forward with elbows on the table. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, sitting beside him looking thoughtful. Then, the exact character in a black hoodie from Image 3, sitting across the table with arms crossed, skeptical expression. A city map hangs on the wall behind them. Use Image 4 as the exact background location. Medium-wide shot, eye-level. Morning light from a small window. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, at a cluttered workbench in a garage, discussing something seriously. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, listening attentively. Then, the exact character in a black hoodie from Image 3, looking unconvinced, leaning back. Tools and a map on the wall behind them. Use Image 4 as the exact background location. Medium shot, eye-level. Soft morning light. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, making a point with his hand, persuasive expression. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, nodding slowly. Then, the exact character in a black hoodie from Image 3, uncrossing his arms, beginning to be convinced. Use Image 4 as the exact background location. Medium shot, eye-level. Morning light. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, looking at the others with determination. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, eyes bright with an idea. Then, the exact character in a black hoodie from Image 3, finally engaged, leaning forward. Use Image 4 as the exact background location. Medium group shot, eye-level. Warm morning light. {ST}",
))

EXT_CLIPS.append(raw("S02_B", "S02",
    "Тако на ведре, болтает ногами — 'Я не смотрел, я оценивал обстановку!'",
    [T, L("garage")],
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, sitting on an upturned bucket in the corner of a garage, feet dangling and swinging. Animated expression, gesturing with one hand while defending himself. Use Image 2 as the exact background location. Medium shot, slight low angle looking up at him. Morning light, warm tones. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, perched on a flipped bucket in a garage corner. Legs swinging, one finger raised in the air making a point. Indignant but funny expression. Use Image 2 as the exact background location. Medium close-up, eye-level. Soft morning light from a small window. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, bouncing excitedly on the bucket. Eyes sparkling. Ready for adventure. Use Image 2 as the exact background location. Medium shot, eye-level. Morning light. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, jumping off the bucket with both fists pumped in the air. Triumphant expression. Use Image 2 as the exact background location. Medium shot, slight low angle. Warm morning light. {ST}",
))

EXT_CLIPS.append(raw("S02_C", "S02",
    "Амин предлагает план — отнести плов. Ая понимающе: 'Предлог?' Тако: 'Операция Плов!'",
    [A, Y, T, L("garage")],
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, speaking to the group with a calm confident look — he has a plan. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, smiling knowingly, one eyebrow raised — she understands the real motive. Then, the exact character in a red-and-white striped shirt and red cap from Image 3, pumping his fist in excitement. Use Image 4 as the exact background location. Medium group shot, eye-level. Morning light. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, laying out a plan to the others, hand gestures showing he's thought this through. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, giving him a knowing look with a slight smirk. Then, the exact character in a red-and-white striped shirt and red cap from Image 3, already on his feet from the bucket, ready to go. Use Image 4 as the exact background location. Medium shot, eye-level. Soft morning light. {ST}",
    f"Three children in a huddle in a garage — a team. The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, at the center, the planner. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, the strategist, nodding approval. Then, the exact character in a red-and-white striped shirt and red cap from Image 3, the eager volunteer, already saluting. Use Image 4 as the exact background location. Medium shot, slight low angle. Morning light through a window. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, standing, decisive. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, picking up her sketchbook, ready. Then, the exact character in a red-and-white striped shirt and red cap from Image 3, bouncing toward the door. Mission accepted. Use Image 4 as the exact background location. Medium-wide shot, eye-level. Warm morning light. {ST}",
))

# ============================================================
# SCENE 1 — Additional clips (+5)
# ============================================================

EXT_CLIPS.append(raw("S01_P", "S01",
    "Крупный план: фургон Джамиля. Тёмно-зелёный, потёртый. Выцветшие наклейки — флажки стран, эмблема института.",
    [L("house_front")],
    f"Close-up of a dark green van parked on a quiet street. Scratched paint, faded stickers on the side — flags of different countries, an institutional emblem, a licence plate from a distant region. Dust on the wheels. Use Image 1 as the exact background location. Close-up, eye-level. Golden hour light, warm tones. {ST}",
    f"A worn dark-green cargo van parked outside a house. Peeling stickers on the side panels — small country flags, a faded research institute logo. The van looks road-weary, like a well-traveled suitcase. Use Image 1 as the exact background location. Medium shot, low angle. Late afternoon sun, long shadows. {ST}",
    f"Detail shot of the dark green van — dented bumper, scratched paint with faded stickers visible, dust coating the lower panels. The rear doors are still closed. Use Image 1 as the exact background location. Close-up, slightly low angle. Golden hour lighting, dust motes in the sunbeams. {ST}",
    f"A dark green van, weathered by many roads, stands still on a quiet residential street. Faded decals of country flags and an old institutional crest are barely visible on its side panels. Use Image 1 as the exact background location. Medium-wide shot, eye-level. Late afternoon golden light. {ST}",
))

EXT_CLIPS.append(raw("S01_Q", "S01",
    "Крупный план: ящики внутри фургона. Маркировка на разных языках. На одном — цифры с точками и буква N.",
    [L("house_front")],
    f"Inside the open rear doors of a van — wooden crates, cardboard boxes, burlap-wrapped bundles packed tightly. Markings in Arabic, English, and other scripts. One crate shows numbers with decimal points and the letter N — geographic coordinates. Use Image 1 as the exact background location. Close-up, eye-level looking into van interior. Afternoon light illuminating the packed cargo. {ST}",
    f"View into the back of an open cargo van — densely packed wooden and cardboard crates of various sizes. Foreign labels and shipping marks visible. On one wooden crate — hand-written numbers with a period and the letter N, suggesting coordinates. Use Image 1 as the exact background location. Close-up, slightly high angle. Golden light streaming into the dim van interior. {ST}",
    f"The open rear of a van reveals a wall of packed crates — wooden boxes with stenciled markings, burlap packages, rolled items. One crate prominently shows handwritten numbers with N — latitude coordinates. Mysterious cargo. Use Image 1 as the exact background location. Close-up, eye-level. Warm afternoon backlight from the open doors. {ST}",
    f"Cargo inside an open van — wooden crates stacked carefully, some wrapped in cloth, labels in multiple scripts. A prominent crate displays decimal numbers and the letter N — coordinates of some distant place. Use Image 1 as the exact background location. Close-up, low angle looking up into the van. Afternoon sunlight catching dust particles inside. {ST}",
))

EXT_CLIPS.append(raw("S01_R", "S01",
    "Симба встаёт, уши торчком, нос работает. Настороженное рычание — новый запах.",
    [SB, L("fence")],
    f"The exact animal from Image 1, preserving identical facial features and proportions, rises from lying position near a wooden fence, ears fully erect, nose twitching, body tense with alertness. Not aggressive — cautious. A new scent in the air. Use Image 2 as the exact background location. Medium shot, low angle. Golden hour light, warm tones. {ST}",
    f"The exact animal from Image 1, preserving identical facial features and proportions, stands alert at a fence gate, ears pointed forward, nostrils flaring, a low rumble in the chest — watchful, not hostile. Sensing something unfamiliar. Use Image 2 as the exact background location. Medium close-up, eye-level. Late afternoon warm light. {ST}",
    f"The exact animal from Image 1, preserving identical facial features and proportions, stands rigid near the fence, ears pricked high, head turned toward something off-screen, body language alert but not threatening — processing a new scent. Use Image 2 as the exact background location. Medium shot, slight low angle. Warm golden light. {ST}",
    f"The exact animal from Image 1, preserving identical facial features and proportions, has risen to all fours by the fence, hackles slightly raised, nose working the air, ears rotating — the posture of a guardian detecting something new. Use Image 2 as the exact background location. Medium close-up, low angle. Golden hour backlight. {ST}",
))

EXT_CLIPS.append(raw("S01_S", "S01",
    "Тако перегибается через забор, вцепившись руками, кричит «Ас-саляму алейкум!»",
    [T, L("fence")],
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, hangs over a wooden fence, gripping the top with both hands, leaning far over the other side, mouth wide open calling out with bold enthusiasm. Use Image 2 as the exact background location. Medium shot, low angle from the other side. Golden hour light, energetic pose. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, clings to the top of a wooden fence, chin resting on his hands, feet dangling off the ground, shouting a greeting with fearless seven-year-old confidence. Use Image 2 as the exact background location. Medium close-up, eye-level. Warm afternoon light. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, stretches over the fence, arms hooked over the top board, leaning as far as possible, face bright with curiosity and boldness, calling out. Use Image 2 as the exact background location. Medium shot, slight low angle. Golden light, playful energy. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, is draped over the fence top, legs kicking behind him, one hand gripping the wood, the other waving, shouting cheerfully. Use Image 2 as the exact background location. Medium-wide shot, low angle. Warm late afternoon glow. {ST}",
))

EXT_CLIPS.append(raw("S01_T", "S01",
    "Симба обнюхивает столб у забора Джамиля. Садится. Смотрит на дверь. Не уходит.",
    [SB, L("jamil_house_front")],
    f"The exact animal from Image 1, preserving identical facial features and proportions, sniffs a fence post near a house entrance, then sits down deliberately, facing the closed front door, watching with patient intensity — not leaving. Use Image 2 as the exact background location. Medium shot, eye-level. Late afternoon golden light, calm atmosphere. {ST}",
    f"The exact animal from Image 1, preserving identical facial features and proportions, sits upright beside a fence post near a neighbor's house, nose at work, then settling into a watchful sit, eyes fixed on the closed door. A sentinel who has chosen his post. Use Image 2 as the exact background location. Medium shot, low angle. Warm sunset tones. {ST}",
    f"The exact animal from Image 1, preserving identical facial features and proportions, has settled at the base of a fence near a house, sitting alert and patient, eyes locked on the front door, ears forward. Waiting. Watching. Not moving. Use Image 2 as the exact background location. Medium shot, eye-level. Golden evening light, peaceful street. {ST}",
    f"The exact animal from Image 1, preserving identical facial features and proportions, sits calmly but attentively near the neighbor's gate, head held high, gazing steadily at the closed door — a self-appointed guardian deciding this is his new post. Use Image 2 as the exact background location. Medium-wide shot, eye-level. Warm late afternoon light. {ST}",
))

# ============================================================
# SCENE 2 — Additional clips (+7)
# ============================================================

EXT_CLIPS.append(raw("S02_D", "S02",
    "Establishing: гараж-мастерская. Верстак, инструменты, карта города на стене.",
    [L("garage")],
    f"Interior of a garage workshop — a workbench with tools, a city map pinned to the wall, light streaming through a small window near the ceiling. The atmosphere of a makeshift headquarters. Use Image 1 as the exact background location. Wide shot, eye-level. Morning light from the high window, dust motes. {ST}",
    f"A garage converted into a workshop-headquarters. Wooden workbench, scattered tools, a large city map on the wall with pins and markers. Light comes from a small window high up. Organized chaos. Use Image 1 as the exact background location. Medium-wide shot, slight low angle. Cool morning light filtering in. {ST}",
    f"A garage workshop interior — cluttered but purposeful. Tools on the bench, a city map on the wall left from a past adventure, wooden crates as seats. Morning light through a high window. Use Image 1 as the exact background location. Wide establishing shot, eye-level. Cool morning atmosphere. {ST}",
    f"Inside a garage workshop — workbench with tools, a detailed city map pinned on the wall, a small window near the ceiling casting a beam of morning light across the space. Use Image 1 as the exact background location. Medium-wide shot, eye-level. Morning light, studious atmosphere. {ST}",
))

EXT_CLIPS.append(raw("S02_E", "S02",
    "Карим скептически: «Ну и что? Пожилой человек переехал.»",
    [K, L("garage")],
    f"The exact character in a black hoodie from Image 1, preserving identical facial features and proportions, sits at a workbench, arms crossed, one eyebrow raised skeptically, expression saying 'so what?' — unimpressed by the news. Use Image 2 as the exact background location. Medium close-up, eye-level. Morning light from a high window. {ST}",
    f"The exact character in a black hoodie from Image 1, preserving identical facial features and proportions, leans back on a stool, arms folded across his chest, a dubious half-smile on his face — the look of someone who needs more convincing. Use Image 2 as the exact background location. Medium shot, eye-level. Cool morning garage light. {ST}",
    f"The exact character in a black hoodie from Image 1, preserving identical facial features and proportions, shrugs with palms up, head tilted, face expressing mild disbelief — clearly unimpressed by the mystery so far. Use Image 2 as the exact background location. Medium close-up, slight low angle. Morning light. {ST}",
    f"The exact character in a black hoodie from Image 1, preserving identical facial features and proportions, sits with crossed arms, chin slightly raised, one eyebrow up in skepticism, the classic 'prove it' expression. Use Image 2 as the exact background location. Medium shot, eye-level. Garage morning light. {ST}",
))

EXT_CLIPS.append(raw("S02_F", "S02",
    "Амин описывает: координаты на ящиках, один без семьи, фургон забит до потолка.",
    [A, L("garage")],
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, leans forward on the workbench, hands flat on the surface, speaking earnestly with intensity in his eyes, making his case to unseen listeners. Use Image 2 as the exact background location. Medium shot, eye-level. Morning light, focused atmosphere. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, gestures with one hand while the other rests on the table, brow furrowed, explaining something urgently, ticking off points on his fingers. Use Image 2 as the exact background location. Medium close-up, eye-level. Garage morning light. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, speaks with controlled excitement, eyes bright, counting reasons on his fingers — making a compelling argument. Use Image 2 as the exact background location. Medium shot, slight low angle. Morning workshop light. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, sits forward on a stool, elbows on knees, hands clasped, presenting his observations with quiet conviction. Use Image 2 as the exact background location. Medium close-up, eye-level. Soft morning light from high window. {ST}",
))

EXT_CLIPS.append(raw("S02_G", "S02",
    "Ая предлагает: «Нужно узнать больше. Но аккуратно — он прикрыл дверь, когда заметил.»",
    [Y, L("garage")],
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, sits composed at the workbench, one hand raised with index finger extended, speaking calmly and thoughtfully — the voice of reason. Use Image 2 as the exact background location. Medium close-up, eye-level. Morning garage light. {ST}",
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, looks at each person in turn as she speaks, measured and careful, hands folded on the table — proposing caution. Use Image 2 as the exact background location. Medium shot, eye-level. Soft morning light. {ST}",
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, raises a cautionary hand, expression serious but kind, reminding the group to be careful and considerate. Use Image 2 as the exact background location. Medium close-up, slight low angle. Morning light. {ST}",
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, speaks with quiet authority, one hand gesturing gently, eyes conveying both caution and curiosity. Use Image 2 as the exact background location. Medium shot, eye-level. Morning workshop atmosphere. {ST}",
))

EXT_CLIPS.append(raw("S02_H", "S02",
    "Тако на перевёрнутом ведре, болтает ногами. «Я не смотрел — я оценивал обстановку!»",
    [T, L("garage")],
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, sits on an upturned bucket in the corner, legs swinging, arms crossed defiantly, chin raised with an expression of wounded professionalism. Use Image 2 as the exact background location. Medium shot, eye-level. Morning garage light. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, perches on an overturned bucket, kicking his feet rhythmically, pointing at his own eyes with two fingers in a 'I was watching' gesture, indignant. Use Image 2 as the exact background location. Medium shot, slight low angle. Morning light from high window. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, sits on a bucket in the corner, legs dangling, face screwed up in defensive pride, one finger raised to make a crucial distinction. Use Image 2 as the exact background location. Medium close-up, eye-level. Garage morning light. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, bounces on an upturned bucket, feet swinging, gesturing emphatically with both hands, face full of seven-year-old indignation at being misunderstood. Use Image 2 as the exact background location. Medium shot, low angle. Morning light. {ST}",
))

EXT_CLIPS.append(raw("S02_I", "S02",
    "Амин предлагает план: «Мама приготовила плов. Что если мы отнесём ему?»",
    [A, K, L("garage")],
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, leans forward with a cunning half-smile, index finger tapping the table — proposing a clever plan. Then, the exact character in a black hoodie from Image 2, listens with growing interest, skepticism fading to a nod. Use Image 3 as the exact background location. Medium shot, eye-level. Morning garage light. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, speaks with a conspiratorial gleam in his eye, palm flat on the table as if laying down cards. Then, the exact character in a black hoodie from Image 2, uncrosses his arms, warming to the idea. Use Image 3 as the exact background location. Medium shot, eye-level. Soft morning light. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, sits up straight with an idea forming on his face, mouth curving into a strategic smile. Then, the exact character in a black hoodie from Image 2, raises his eyebrows in approval. Use Image 3 as the exact background location. Medium close-up, eye-level. Morning light from above. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, gestures with both hands, outlining a plan, expression brightening. Then, the exact character in a black hoodie from Image 2, nods slowly, the first sign of engagement. Use Image 3 as the exact background location. Medium shot, eye-level. Morning garage atmosphere. {ST}",
))

EXT_CLIPS.append(raw("S02_J", "S02",
    "Тако радостно: «Операция Плов! Принято!» Подпрыгивает на ведре.",
    [T, L("garage")],
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, leaps off the upturned bucket with both fists pumped in the air, face exploding with excitement, legs mid-jump — pure seven-year-old enthusiasm. Use Image 2 as the exact background location. Medium shot, low angle. Morning light, dynamic pose. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, springs up from his bucket seat, arms thrown wide in celebration, red cap slightly askew, beaming with mission-accepted energy. Use Image 2 as the exact background location. Medium shot, slight low angle. Bright morning light. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, jumps to his feet from the bucket, saluting with one hand while the other is a triumphant fist, face lit up with purpose and joy. Use Image 2 as the exact background location. Medium shot, eye-level. Morning garage light, energetic. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, bounces off the bucket mid-jump, both hands in the air, grinning ear to ear, the bucket wobbling behind him — maximum excitement. Use Image 2 as the exact background location. Medium shot, low angle capturing the jump. Morning light. {ST}",
))

# ============================================================
# SCENE 4 — Additional clips (+9)
# ============================================================

EXT_CLIPS.append(raw("S04_H", "S04",
    "Establishing: кухня, семья за столом. Тарелки, хлеб, чай. Тёплый семейный вечер.",
    [L("kitchen")],
    f"A warm family kitchen — a dining table set with plates of food, flatbread, steaming tea cups. The kitchen is well-lit, homey, and lived-in. An empty but inviting scene ready for a family dinner. Use Image 1 as the exact background location. Wide shot, eye-level. Warm evening lighting, cozy atmosphere. {ST}",
    f"A family kitchen at dinnertime — wooden table laden with dishes, bread, a teapot. Warm light from overhead, steam rising from the food. The feeling of a loving home. Use Image 1 as the exact background location. Medium-wide shot, slightly high angle. Warm golden interior light. {ST}",
    f"A family dinner table in a warm kitchen — plates of food, fresh bread, glasses of tea. Steam rises from the dishes. Everything speaks of home and warmth. Use Image 1 as the exact background location. Wide establishing shot, eye-level. Warm interior evening light, inviting. {ST}",
    f"A kitchen dining table set for family dinner — multiple plates, flatbread in a basket, a teapot, glasses. Warm, inviting light fills the room. The heart of the home. Use Image 1 as the exact background location. Medium-wide shot, eye-level. Golden evening kitchen light. {ST}",
))

EXT_CLIPS.append(raw("S04_I", "S04",
    "Тако рассказывает с набитым ртом, размахивая вилкой, с драматическими паузами.",
    [T, L("kitchen")],
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, sits at a dinner table, mouth full, one hand waving a fork dramatically, the other gesturing at invisible huge crates — mid-story, eyes wide with excitement. Use Image 2 as the exact background location. Medium close-up, eye-level. Warm kitchen evening light. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, talks animatedly at the dinner table, cheeks puffed with food, fork swinging in the air for emphasis, creating a one-man theatrical performance. Use Image 2 as the exact background location. Medium shot, eye-level. Warm family dinner lighting. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, leans forward at the table, fork mid-air, mouth still chewing, eyes enormous as he describes something amazing — completely lost in his own story. Use Image 2 as the exact background location. Medium close-up, slight low angle. Warm kitchen light. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, gestures wildly with his fork at the dinner table, making dramatic pauses between bites, face animated with the urgency of his tale. Use Image 2 as the exact background location. Medium shot, eye-level. Golden evening light. {ST}",
))

EXT_CLIPS.append(raw("S04_J", "S04",
    "Мама строго: «Тако, не разговаривай с набитым ртом.»",
    [M, L("kitchen")],
    f"The exact character in a black hijab and black abaya from Image 1, preserving identical facial features and proportions, looks across the dinner table with a firm but loving expression, one hand raised slightly in a gentle 'stop' gesture, the universal mother's look of mild exasperation. Use Image 2 as the exact background location. Medium close-up, eye-level. Warm kitchen evening light. {ST}",
    f"The exact character in a black hijab and black abaya from Image 1, preserving identical facial features and proportions, gives a pointed look across the table, eyebrows slightly raised, lips pursed — patient but firm maternal correction. Use Image 2 as the exact background location. Medium shot, eye-level. Warm family dinner lighting. {ST}",
    f"The exact character in a black hijab and black abaya from Image 1, preserving identical facial features and proportions, pauses with her teacup, looking at her youngest with that particular motherly mix of love and 'behave yourself' firmness. Use Image 2 as the exact background location. Medium close-up, eye-level. Golden evening kitchen light. {ST}",
    f"The exact character in a black hijab and black abaya from Image 1, preserving identical facial features and proportions, turns toward the excited chatter with a calm but authoritative expression, one finger lightly raised — the correction delivered with warmth beneath the firmness. Use Image 2 as the exact background location. Medium shot, eye-level. Warm interior light. {ST}",
))

EXT_CLIPS.append(raw("S04_K", "S04",
    "Папа слушает спокойно: «Может, просто неловко. Только переехал.»",
    [P, L("kitchen")],
    f"The exact character in a black turtleneck sweater and glasses from Image 1, preserving identical facial features and proportions, sits at the head of the dinner table, leaning back in his chair with a calm, measured expression, one hand on his tea glass — the reasonable voice of adult perspective. Use Image 2 as the exact background location. Medium close-up, eye-level. Warm kitchen evening light. {ST}",
    f"The exact character in a black turtleneck sweater and glasses from Image 1, preserving identical facial features and proportions, listens patiently at the dinner table, a slight understanding smile, hands folded, offering a sensible alternative explanation. Use Image 2 as the exact background location. Medium shot, eye-level. Warm family dinner atmosphere. {ST}",
    f"The exact character in a black turtleneck sweater and glasses from Image 1, preserving identical facial features and proportions, speaks calmly at the dinner table, palm open in a 'let's be reasonable' gesture, glasses reflecting the kitchen light. Use Image 2 as the exact background location. Medium close-up, eye-level. Warm interior evening light. {ST}",
    f"The exact character in a black turtleneck sweater and glasses from Image 1, preserving identical facial features and proportions, sits comfortably, tea in hand, expression of gentle wisdom — offering the adults' perspective with patient authority. Use Image 2 as the exact background location. Medium shot, eye-level. Golden kitchen light. {ST}",
))

EXT_CLIPS.append(raw("S04_L", "S04",
    "Ая поддерживает папу: «Не каждый старик с ящиками — тайна.» Тако: «Каждый.»",
    [Y, T, L("kitchen")],
    f"First, the exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, speaks at the dinner table with a reasonable expression, palms up in a calming gesture. Then, the exact character in a red-and-white striped shirt and red cap from Image 2, crosses his arms and responds with absolute certainty, chin raised in defiance. Use Image 3 as the exact background location. Medium shot, eye-level. Warm kitchen light. {ST}",
    f"First, the exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, tilts her head diplomatically at the table, trying to keep things in perspective. Then, the exact character in a red-and-white striped shirt and red cap from Image 2, leans forward with a single emphatic word on his lips, expression of total conviction. Use Image 3 as the exact background location. Medium two-shot, eye-level. Evening family dinner light. {ST}",
    f"First, the exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, makes a calming gesture at the table, being the voice of reason. Then, the exact character in a red-and-white striped shirt and red cap from Image 2, shakes his head firmly, arms crossed, utterly unconvinced. Use Image 3 as the exact background location. Medium shot, eye-level. Warm golden kitchen light. {ST}",
    f"First, the exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, looks at her younger brother with patient exasperation across the table. Then, the exact character in a red-and-white striped shirt and red cap from Image 2, sits rigid with crossed arms and a stubborn set jaw — he will not budge on this. Use Image 3 as the exact background location. Medium close-up two-shot, eye-level. Kitchen evening light. {ST}",
))

EXT_CLIPS.append(raw("S04_M", "S04",
    "Папа замирает: «Фахри... Имя знакомое.» Ложка в воздухе.",
    [P, L("kitchen")],
    f"The exact character in a black turtleneck sweater and glasses from Image 1, preserving identical facial features and proportions, freezes mid-bite at the dinner table, spoon suspended in the air, eyes narrowing as a memory surfaces — recognition flickering across his face. Use Image 2 as the exact background location. Close-up, eye-level. Warm kitchen light, a moment of stillness. {ST}",
    f"The exact character in a black turtleneck sweater and glasses from Image 1, preserving identical facial features and proportions, stops eating suddenly, utensil hovering, brow furrowed in thought — the name has triggered something in his memory, he's searching for it. Use Image 2 as the exact background location. Close-up, eye-level. Warm evening light, the table blurred behind. {ST}",
    f"The exact character in a black turtleneck sweater and glasses from Image 1, preserving identical facial features and proportions, pauses with his spoon in mid-air, a look of distant recognition crossing his face, lips slightly parted as if about to remember something. Use Image 2 as the exact background location. Close-up, eye-level. Golden kitchen light on his thoughtful face. {ST}",
    f"The exact character in a black turtleneck sweater and glasses from Image 1, preserving identical facial features and proportions, has gone still at the table, eyes focused inward, spoon forgotten in his hand — the name has sparked a distant, half-buried memory. Use Image 2 as the exact background location. Close-up, eye-level. Warm interior light, moment of tension. {ST}",
))

EXT_CLIPS.append(raw("S04_N", "S04",
    "Амин и Ая быстро переглядываются после реакции папы.",
    [A, Y, L("kitchen")],
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, glances quickly sideways across the dinner table, eyes locking with his sister — a wordless 'did you catch that?' look. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, returns the look with a subtle nod, barely perceptible. Use Image 3 as the exact background location. Close-up two-shot, eye-level. Warm kitchen light, a brief charged moment. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, shoots a quick meaningful glance at his sister, eyebrows slightly raised in silent communication. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, meets his eyes for half a second, understanding passing between them instantly. Use Image 3 as the exact background location. Close-up, eye-level. Warm evening dinner light. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, looks across the table at his sister with sharp awareness, a barely visible 'are you thinking what I'm thinking' expression. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, gives the tiniest nod, eyes bright with shared understanding. Use Image 3 as the exact background location. Medium close-up two-shot, eye-level. Kitchen evening light. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, freezes for a split second, then his eyes slide toward his sister — quick, deliberate, meaningful. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, catches the glance and holds it, lips pressing together — message received. Use Image 3 as the exact background location. Close-up, eye-level. Warm golden kitchen light. {ST}",
))

EXT_CLIPS.append(raw("S04_O", "S04",
    "Амин просит у папы разрешения: «Можно в энциклопедии посмотрю? У тебя в кабинете?»",
    [A, P, L("kitchen")],
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, leans toward his father across the dinner table, face composed but eager, asking permission with respectful casualness. Then, the exact character in a black turtleneck sweater and glasses from Image 2, nods easily with a warm 'of course' expression. Use Image 3 as the exact background location. Medium shot, eye-level. Warm kitchen evening light. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, addresses his father at the table, tone casual but eyes intent — trying not to seem too eager. Then, the exact character in a black turtleneck sweater and glasses from Image 2, gestures with his hand — 'go ahead', unsuspecting. Use Image 3 as the exact background location. Medium two-shot, eye-level. Warm family dinner atmosphere. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, pushes back from the table slightly, looking at his father with a practiced casual expression masking excitement. Then, the exact character in a black turtleneck sweater and glasses from Image 2, nods and smiles, returning to his meal. Use Image 3 as the exact background location. Medium shot, eye-level. Golden evening light. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, asks something of his father across the table, voice calm, hands in lap, the picture of innocent curiosity. Then, the exact character in a black turtleneck sweater and glasses from Image 2, waves a permissive hand, pleased by his son's scholarly interest. Use Image 3 as the exact background location. Medium close-up, eye-level. Warm kitchen light. {ST}",
))

EXT_CLIPS.append(raw("S04_P", "S04",
    "Вся семья за столом — широкий план семейного ужина.",
    [P, M, A, L("kitchen")],
    f"First, the exact character in a black turtleneck sweater and glasses from Image 1, preserving identical facial features and proportions, sits at the head of the dinner table. Then, the exact character in a black hijab and black abaya from Image 2, sits beside him, serving tea. Then, the exact character in a grey hoodie from Image 3, sits across, reaching for bread. A warm family dinner scene. Use Image 4 as the exact background location. Wide shot, slightly high angle. Warm golden evening kitchen light. {ST}",
    f"First, the exact character in a black turtleneck sweater and glasses from Image 1, preserving identical facial features and proportions, presides at the family dinner table with a content expression. Then, the exact character in a black hijab and black abaya from Image 2, pours tea from a pot. Then, the exact character in a grey hoodie from Image 3, listens attentively while eating. Use Image 4 as the exact background location. Wide shot, eye-level. Warm family dinner atmosphere. {ST}",
    f"First, the exact character in a black turtleneck sweater and glasses from Image 1, preserving identical facial features and proportions, holds his tea glass, relaxed. Then, the exact character in a black hijab and black abaya from Image 2, passes bread across the table. Then, the exact character in a grey hoodie from Image 3, eats while thinking. A complete family dinner scene. Use Image 4 as the exact background location. Medium-wide shot, slightly high angle. Warm evening light. {ST}",
    f"First, the exact character in a black turtleneck sweater and glasses from Image 1, preserving identical facial features and proportions, smiles at the table. Then, the exact character in a black hijab and black abaya from Image 2, arranges dishes with care. Then, the exact character in a grey hoodie from Image 3, looks at his father while eating. Use Image 4 as the exact background location. Wide establishing shot, eye-level. Golden kitchen light, family warmth. {ST}",
))

# ============================================================
# SCENE 5 — Additional clips (+8)
# ============================================================

EXT_CLIPS.append(raw("S05_E", "S05",
    "Establishing: кабинет папы. Книжные полки до потолка, тёплая лампа на столе.",
    [L("kabinet")],
    f"A scholarly home office — bookshelves reaching to the ceiling, stacked with books and journals. A warm desk lamp casts a golden pool of light on a wooden desk. Academic atmosphere — this is a room of a well-read man. Use Image 1 as the exact background location. Wide establishing shot, eye-level. Warm lamp light, evening. {ST}",
    f"Interior of a study — floor-to-ceiling bookshelves packed with volumes, a wooden desk with a brass lamp casting warm light. Papers and journals stacked neatly. The room of someone who values knowledge. Use Image 1 as the exact background location. Medium-wide shot, slight low angle. Warm evening lamplight. {ST}",
    f"A home study filled with books — tall shelves line every wall, a classic desk lamp illuminates the workspace, old journals and reference books visible. Quiet, intellectual atmosphere. Use Image 1 as the exact background location. Wide shot, eye-level. Golden lamp light against dark evening windows. {ST}",
    f"The warmly-lit study of an intellectual — bookshelves everywhere, a desk lamp creating a circle of golden light, academic journals on the lower shelves. A room that invites discovery. Use Image 1 as the exact background location. Medium-wide shot, eye-level. Warm evening lamplight, cozy scholarly atmosphere. {ST}",
))

EXT_CLIPS.append(raw("S05_F", "S05",
    "Амин и Карим листают старые научные журналы. Быстро, но внимательно.",
    [A, K, L("kabinet")],
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, sits at a desk flipping through old scientific journals, fingers moving quickly but eyes scanning each page carefully. Then, the exact character in a black hoodie from Image 2, sits beside him with another stack, leafing through. Use Image 3 as the exact background location. Medium shot, eye-level. Warm desk lamp light, evening. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, hunches over open journals on a desk, turning pages rapidly, searching. Then, the exact character in a black hoodie from Image 2, runs his finger down a page, scanning for a name. Use Image 3 as the exact background location. Medium shot, slight high angle over shoulders. Warm lamplight. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, flips through yellowed pages of old journals, concentrated. Then, the exact character in a black hoodie from Image 2, picks up another journal from the stack, opens it, scans. Two researchers at work. Use Image 3 as the exact background location. Medium shot, eye-level. Golden lamp light, focused atmosphere. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, turns journal pages with practiced speed, eyes sharp. Then, the exact character in a black hoodie from Image 2, leans closer to a page, squinting at small text. Use Image 3 as the exact background location. Medium close-up, eye-level. Warm lamplight illuminating the pages. {ST}",
))

EXT_CLIPS.append(raw("S05_G", "S05",
    "Карим находит! «Вот!» Раскрытая страница с фотографией.",
    [K, L("kabinet")],
    f"The exact character in a black hoodie from Image 1, preserving identical facial features and proportions, suddenly stops flipping, finger landing on a page, face lighting up with discovery — eyes wide, mouth forming an excited exclamation, tapping the page urgently. Use Image 2 as the exact background location. Medium close-up, eye-level. Warm desk lamp light, moment of discovery. {ST}",
    f"The exact character in a black hoodie from Image 1, preserving identical facial features and proportions, freezes mid-page-turn, then leans in close, finger pointing at something on the open journal page, turning to look at his companion with triumph. Use Image 2 as the exact background location. Medium shot, eye-level. Golden lamplight, excitement visible. {ST}",
    f"The exact character in a black hoodie from Image 1, preserving identical facial features and proportions, slams his hand flat on an open journal page in excitement, half-standing from his chair, the thrill of discovery on his face. Use Image 2 as the exact background location. Medium close-up, slight low angle. Warm lamp light. {ST}",
    f"The exact character in a black hoodie from Image 1, preserving identical facial features and proportions, points emphatically at an open journal, bouncing in his seat, the 'I found it' moment written across his entire body language. Use Image 2 as the exact background location. Medium shot, eye-level. Desk lamp illumination, moment of breakthrough. {ST}",
))

EXT_CLIPS.append(raw("S05_H", "S05",
    "Крупный план: раскрытая страница журнала. Фотография молодого Фахри в полевой куртке на фоне скалистого ландшафта.",
    [L("kabinet")],
    f"Close-up of an open scientific journal page — a black-and-white photograph of a young man in a field jacket against a rocky landscape, smiling at the camera with sharp intelligent eyes. Caption below: expedition text in small print. The page is yellowed with age. Use Image 1 as the exact background location. Close-up, straight down on the desk. Warm desk lamp light on the page. {ST}",
    f"An old scientific journal lies open on a desk — a grainy photograph shows a younger version of a man in field clothes, standing before a mountainous landscape, sunburnt and smiling confidently. Academic text surrounds the photo. Use Image 1 as the exact background location. Close-up, slight angle. Warm lamplight illuminating the page details. {ST}",
    f"Close-up of a journal article — a photograph of a young geologist in field gear against a rocky terrain, confident smile, intelligent eyes. The page lists expedition details, publication names, dates. Old paper, slightly foxed. Use Image 1 as the exact background location. Close-up, top-down angle. Golden desk lamp light. {ST}",
    f"An open journal on a wooden desk showing a photograph of a young field researcher — tanned, wearing a practical jacket, with the same perceptive eyes, standing before a vast geological landscape. Academic credentials listed below. Use Image 1 as the exact background location. Close-up, angled. Warm lamp light on yellowed pages. {ST}",
))

EXT_CLIPS.append(raw("S05_I", "S05",
    "Амин читает вслух, водит пальцем: «Кафедра геологии... 42 публикации... 14 экспедиций...»",
    [A, L("kabinet")],
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, leans over an open journal on a desk, index finger tracing lines of text, lips moving as he reads aloud, eyes widening with each new detail — growing realization on his face. Use Image 2 as the exact background location. Close-up, eye-level. Warm desk lamp light illuminating his concentrated face. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, reads intently from an open journal, finger sliding along the text, brow furrowed in concentration, expression shifting from curiosity to awe as the scale of what he's reading sinks in. Use Image 2 as the exact background location. Medium close-up, slight high angle over shoulder. Warm lamplight. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, bent over a journal, reading aloud, finger on the text, face illuminated by the desk lamp — each fact he reads deepening the mystery and his fascination. Use Image 2 as the exact background location. Close-up, eye-level. Golden desk lamp light. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, traces text in the journal with his fingertip, reading each line carefully, expression growing more serious — this is no ordinary neighbor. Use Image 2 as the exact background location. Medium close-up, over-shoulder. Warm evening lamplight. {ST}",
))

EXT_CLIPS.append(raw("S05_J", "S05",
    "Карим присвистывает: «14 экспедиций. Это не дилетант.»",
    [K, L("kabinet")],
    f"The exact character in a black hoodie from Image 1, preserving identical facial features and proportions, leans back in his chair, letting out a low whistle, eyebrows raised high, genuinely impressed — arms crossed, head shaking slowly with appreciation. Use Image 2 as the exact background location. Medium close-up, eye-level. Warm lamplight, evening study atmosphere. {ST}",
    f"The exact character in a black hoodie from Image 1, preserving identical facial features and proportions, sits back with widened eyes, lips pursed in an impressed whistle, one hand on the journal page — the skeptic is now fully convinced. Use Image 2 as the exact background location. Medium shot, eye-level. Desk lamp illumination. {ST}",
    f"The exact character in a black hoodie from Image 1, preserving identical facial features and proportions, rocks back in his chair, eyebrows up, mouth shaped in a silent whistle of respect — his earlier skepticism completely evaporated. Use Image 2 as the exact background location. Medium close-up, eye-level. Warm study lighting. {ST}",
    f"The exact character in a black hoodie from Image 1, preserving identical facial features and proportions, shakes his head slowly in admiration, eyes wide, the number sinking in — whatever he expected, this exceeds it. Use Image 2 as the exact background location. Medium shot, eye-level. Golden lamplight. {ST}",
))

EXT_CLIPS.append(raw("S05_K", "S05",
    "Амин: «Последняя — 12 лет назад. И после неё... ничего. Как будто человек исчез.»",
    [A, L("kabinet")],
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, flips further through the journal, finding nothing more, expression shifting to troubled confusion — turning empty pages, the absence of information speaking louder than any article. Use Image 2 as the exact background location. Medium close-up, eye-level. Warm lamp light, the mood darkening. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, looks up from the journal with a troubled frown, closing the publication slowly — the trail has gone cold, the disappearance confirmed. Use Image 2 as the exact background location. Medium shot, eye-level. Desk lamp casting shadows, evening. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, stares at a blank page where more articles should be, realization settling on his face — something happened twelve years ago that erased this man from the record. Use Image 2 as the exact background location. Close-up, eye-level. Warm but somber lamplight. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, slowly closes the journal, pressing his palm flat on the cover, expression grave — a brilliant career that simply... stopped. Use Image 2 as the exact background location. Medium close-up, eye-level. Evening lamp light, dust visible in the air. {ST}",
))

EXT_CLIPS.append(raw("S05_L", "S05",
    "Амин закрывает журнал, смотрит на Карима: «Нужно поговорить с ним.» Свет лампы, пыль в воздухе.",
    [A, K, L("kabinet")],
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, places a closed journal on the desk, looking up at his friend with determination — the decision is made. Then, the exact character in a black hoodie from Image 2, meets his gaze and nods slowly — agreed. Use Image 3 as the exact background location. Medium shot, eye-level. Warm desk lamp light, dust motes floating, evening gravity. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, pushes the journal to the center of the desk, jaw set with resolve, looking directly at his companion. Then, the exact character in a black hoodie from Image 2, uncrosses his arms, posture straightening — they're doing this. Use Image 3 as the exact background location. Medium two-shot, eye-level. Golden lamplight, serious mood. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, rests both hands on the closed journal, spine straight, expression resolute. Then, the exact character in a black hoodie from Image 2, leans forward, elbows on the desk — ready to plan the next move. Use Image 3 as the exact background location. Medium shot, eye-level. Warm lamp light, evening study. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, taps the journal cover once, decisively, then looks at his friend. Then, the exact character in a black hoodie from Image 2, holds the look and gives a firm single nod. Use Image 3 as the exact background location. Medium close-up two-shot, eye-level. Desk lamp illumination, significant moment. {ST}",
))

# ============================================================
# SCENE 7 — Additional clips (+9)
# ============================================================

EXT_CLIPS.append(raw("S07_F", "S07",
    "Establishing: ночная комната Амина. Поздно. Дом спит. Книга открыта на кровати.",
    [L("amin_room")],
    f"A bedroom at night — a desk lamp casts dim light, an open book lies abandoned on the bed, the window shows darkness outside. Late night, the house is quiet. A room of a thinking teenager. Use Image 1 as the exact background location. Wide shot, eye-level. Dim nighttime lamp light, blue tones from the window. {ST}",
    f"A quiet bedroom late at night. The desk lamp is on low, an open book face-down on the rumpled bed. Through the window — darkness, a distant streetlight. The stillness of a house asleep. Use Image 1 as the exact background location. Medium-wide shot, eye-level. Soft lamp glow mixed with cool moonlight from window. {ST}",
    f"Interior of a teenager's bedroom at night — lamp on, book open on the bed, everything quiet. Through the window, the street below is dark and empty. Late night insomnia atmosphere. Use Image 1 as the exact background location. Wide establishing shot, eye-level. Mixed warm lamp and cool blue window light. {ST}",
    f"A bedroom in the dead of night — the reading lamp creates a small warm island in the darkness, an open book abandoned on the sheets, the window a rectangle of deep blue. Silence. Use Image 1 as the exact background location. Medium-wide shot, eye-level. Night lighting, atmospheric. {ST}",
))

EXT_CLIPS.append(raw("S07_G", "S07",
    "Амин у окна. Смотрит на дом Джамиля. Свет в окне соседа горит.",
    [A, L("amin_room")],
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, stands at the bedroom window, face lit by cool moonlight, looking out into the night — across the way, a neighbor's window glows warmly. Silhouette visible inside. Use Image 2 as the exact background location. Medium shot, slight side angle. Moonlight on face, warm glow from distant window. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, presses close to the window glass, peering out at the neighboring house — a single lit window across the street, a shadow moving behind it. Use Image 2 as the exact background location. Medium close-up, profile. Cool blue moonlight, warm distant window glow. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, leans against the window frame, watching the house next door — the old man's light is still on, a silhouette paces inside. Late night vigil. Use Image 2 as the exact background location. Medium shot, eye-level from inside the room. Moonlight and distant warm light. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, stands motionless at the window, face illuminated by pale moonlight, watching a lit window in the neighboring house where a figure moves restlessly. Use Image 2 as the exact background location. Medium close-up, eye-level. Cool night tones, warm distant glow. {ST}",
))

EXT_CLIPS.append(raw("S07_H", "S07",
    "Свет в окне Джамиля гаснет. Тишина. Амин вздыхает, отходит от окна.",
    [A, L("amin_room")],
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, still at the window, watches as the light across the street goes dark — the neighboring house swallowed by shadow. He sighs, shoulders dropping, stepping back from the glass. Use Image 2 as the exact background location. Medium shot, eye-level. Full moonlight now, no warm glow. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, sees the neighbor's light click off, leaving only darkness outside. A deep breath, a step back from the window, rubbing tired eyes. Use Image 2 as the exact background location. Medium close-up, profile. Cool blue moonlight only. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, turns away from the dark window, the neighbor's light having just gone out. He looks exhausted but his mind is still racing. Heading toward the bed. Use Image 2 as the exact background location. Medium shot, eye-level. Dim room, moonlight from the window behind him. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, watches the last light go out across the street, then slowly turns from the window with a thoughtful sigh, dragging himself toward sleep. Use Image 2 as the exact background location. Medium shot, three-quarter view. Night blue tones, atmospheric. {ST}",
))

EXT_CLIPS.append(raw("S07_I", "S07",
    "Звук мотора. Амин замирает. Возвращается к окну, прижимается к стеклу.",
    [A, L("amin_room")],
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, freezes mid-step, head snapping toward the window — hearing something. Then rushes back, pressing his face against the glass, eyes wide, breath fogging the pane. Use Image 2 as the exact background location. Medium shot, eye-level. Dark room, moonlight, sudden tension. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, stops dead, body rigid, ear turned toward the window. Then moves fast — back to the glass, hands cupped around his eyes to see better, peering down into the dark street. Use Image 2 as the exact background location. Medium close-up, profile. Cool moonlight, high tension. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, jerks upright at a sound, then presses himself flat against the window, nose to the glass, scanning the dark street below with urgent focus. Heart racing visible in his tense posture. Use Image 2 as the exact background location. Medium shot, side angle. Blue moonlight, tense atmosphere. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, was heading to bed but freezes — a sound outside. In two steps he's at the window again, forehead against the cold glass, breath making a circle of fog, eyes searching the darkness below. Use Image 2 as the exact background location. Close-up, profile. Moonlight on face, fear and curiosity. {ST}",
))

EXT_CLIPS.append(raw("S07_J", "S07",
    "Вид из окна: тёмная машина без фар останавливается у дома Джамиля.",
    [L("night_street")],
    f"A dark car with no headlights sits silently on a moonlit residential street, stopped outside an old house. No lights, no movement. The car is barely visible in the darkness — a menacing shape. Use Image 1 as the exact background location. Wide shot from above (window view), slightly high angle. Moonlight, blue-grey tones, ominous stillness. {ST}",
    f"A quiet nighttime street seen from a high window — a dark vehicle without headlights has stopped in front of a neighbor's house. The engine has gone silent. Moonlight barely outlines the car's shape. Threatening atmosphere. Use Image 1 as the exact background location. Wide shot, high angle (looking down from window). Cool moonlight, deep shadows, tension. {ST}",
    f"Nighttime view of a street from above — a dark car sits motionless without lights near a house entrance. Moonlight filters through clouds, casting shifting shadows. Something is very wrong about this scene. Use Image 1 as the exact background location. Wide shot, bird's-eye from a window. Pale moonlight, ominous blue-grey tones. {ST}",
    f"A dark vehicle, headlights off, parked silently on a moonlit street in front of an old house. No sound, no movement. The car is almost invisible in the shadows. Use Image 1 as the exact background location. Wide shot, high angle from a second-floor window. Blue moonlight, threatening silence. {ST}",
))

EXT_CLIPS.append(raw("S07_K", "S07",
    "Человек в капюшоне выходит из машины. Идёт к двери. Кладёт бумагу на порог.",
    [L("night_street")],
    f"A hooded figure in a dark jacket steps out of a car on a moonlit street, walks slowly toward a house door. In one hand — something white, a folded paper. The figure places it on the doorstep. No face visible — just the hood and dark clothing. Use Image 1 as the exact background location. Medium-wide shot, high angle from window. Moonlight, deep shadows, sinister. {ST}",
    f"A dark silhouette — hooded, in a black jacket — approaches a house door on a quiet night street. Moving deliberately. Places a white sheet of paper on the threshold. Then turns and walks back toward the dark car. Use Image 1 as the exact background location. Medium shot, high angle. Cool moonlight, threatening atmosphere. {ST}",
    f"A figure in a dark hood walks to a house entrance on a moonlit street. Something white in hand — a note. Bends down, places it carefully on the doorstep. Straightens up. Turns back toward a waiting car. All silent. Use Image 1 as the exact background location. Medium-wide shot, high angle. Blue-grey moonlight, cinematic tension. {ST}",
    f"On a silent night street, a hooded person in dark clothing approaches a door, crouches briefly to leave something white on the step, then retreats swiftly to a waiting dark car. Methodical. Practiced. Use Image 1 as the exact background location. Medium shot, elevated angle. Pale moonlight, noir atmosphere. {ST}",
))

EXT_CLIPS.append(raw("S07_L", "S07",
    "Машина уезжает без фар. Амин стоит у окна — сердце колотится.",
    [A, L("amin_room")],
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, stands frozen at the bedroom window, one hand gripping the curtain, face pale in the moonlight, eyes wide with shock — watching a dark shape disappear down the street. Breathing hard. Use Image 2 as the exact background location. Medium close-up, three-quarter view. Moonlight on shocked face. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, presses against the window, watching the dark car vanish without lights, his reflection in the glass showing fear and determination mixed together. Chest heaving with adrenaline. Use Image 2 as the exact background location. Close-up, face reflected in dark window. Cool moonlight, emotional. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, grips the windowsill with white knuckles, staring out at the now-empty dark street, mouth slightly open, processing what he just witnessed. Heart pounding visibly. Use Image 2 as the exact background location. Medium close-up, profile at window. Blue moonlight, aftermath of fear. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, remains at the window, motionless, the street now empty and dark again. His hand trembles slightly on the glass. He saw everything. Use Image 2 as the exact background location. Medium shot, eye-level, facing the dark window. Night lighting, shock and resolve. {ST}",
))

EXT_CLIPS.append(raw("S07_M", "S07",
    "Амин хватает блокнот. Пишет быстро: «Тёмная машина. Без фар. ~01:15.»",
    [A, L("amin_room")],
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, grabs a notebook and pen from the nightstand, sits on the bed edge, writing frantically — capturing every detail before they fade. Hands slightly shaking. Use Image 2 as the exact background location. Medium close-up, high angle over shoulder. Dim lamp light on the notebook page. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, hunches over a notebook on his knees, pen flying across the page, brow furrowed in concentration — writing everything he saw, every detail, times, descriptions. Use Image 2 as the exact background location. Medium shot, eye-level. Desk lamp light, urgent late-night atmosphere. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, scribbles rapidly in a notebook, sitting on the bed, the pen a blur — recording observations with the precision of a trained investigator while the memory is fresh. Use Image 2 as the exact background location. Close-up on hands writing, face partially visible. Warm lamp light on pages. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, writes with urgent speed in a notebook, stopping to think, then writing again — trying to remember the license plate, the time, every detail of the dark visitor. Use Image 2 as the exact background location. Medium close-up, eye-level. Night lamp light, tense atmosphere. {ST}",
))

EXT_CLIPS.append(raw("S07_N", "S07",
    "Амин откладывает блокнот. Руки дрожат. Смотрит на тёмный дом Джамиля.",
    [A, L("amin_room")],
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, sets the notebook down slowly, stares at his trembling hands for a moment, then looks back toward the window — the neighbor's dark house across the street. Something has changed. Use Image 2 as the exact background location. Medium shot, eye-level. Dim lamp and moonlight, somber mood. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, places the pen on the notebook, flexes his shaking fingers, then turns to face the window — looking at the dark, silent house next door. It was real. It happened. Use Image 2 as the exact background location. Medium close-up, three-quarter view. Mixed lamp and moonlight, quiet dread. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, holds his own hands to stop the trembling, takes a deep breath, then looks one more time at the neighbor's dark window across the street. The night is still. As if nothing happened. But it did. Use Image 2 as the exact background location. Medium shot, eye-level. Night atmosphere, blue and warm tones mixed. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, sits on the bed edge, notebook beside him, staring at his slightly trembling hands in the lamp light. Then lifts his eyes to the dark window, the dark house. Resolve forming behind the fear. Use Image 2 as the exact background location. Medium close-up, eye-level. Night lamp light, emotional. {ST}",
))

# ============================================================
# SCENE 8 — Additional clips (+7)
# ============================================================

EXT_CLIPS.append(raw("S08_D", "S08",
    "Establishing: утренний гараж. Резкий свет из окна. Все четверо. Амин невыспавшийся.",
    [A, K, L("garage")],
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, stands at the workbench in the morning-lit garage, dark circles under his eyes, jaw set — he didn't sleep, but he's focused. Then, the exact character in a black hoodie from Image 2, sits on a crate, alert. Use Image 3 as the exact background location. Medium-wide shot, eye-level. Sharp morning light through high window. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, leans against the workbench, tired but wired, hair slightly messy from a sleepless night. Then, the exact character in a black hoodie from Image 2, faces him, arms on knees, listening. Use Image 3 as the exact background location. Medium shot, eye-level. Bright morning garage light. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, paces in the garage, visibly tired but running on adrenaline, dark under-eye circles. Then, the exact character in a black hoodie from Image 2, watches with concern. Use Image 3 as the exact background location. Medium shot, eye-level. Cool sharp morning light. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, sits at the workbench, hands flat on the surface, exhausted but resolute, bags under his eyes. Then, the exact character in a black hoodie from Image 2, leans forward listening intently. Use Image 3 as the exact background location. Medium two-shot, eye-level. Morning light from window. {ST}",
))

EXT_CLIPS.append(raw("S08_E", "S08",
    "Амин докладывает: тёмная машина, без фар, час ночи, капюшон, что-то на пороге.",
    [A, L("garage")],
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, speaks in the garage, one hand on a notebook with his night observations, voice low and serious, recounting what he witnessed — the gravity of the situation clear on his face. Use Image 2 as the exact background location. Medium close-up, eye-level. Sharp morning light. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, holds up his notebook, reading from his scrawled notes, tapping each point — time, description, direction — with methodical precision despite his exhaustion. Use Image 2 as the exact background location. Medium shot, eye-level. Morning garage light, serious briefing atmosphere. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, recounts the night's events, gesturing toward the window as if the street is visible from here, voice tight with controlled urgency. Use Image 2 as the exact background location. Medium close-up, eye-level. Cool morning light, tense. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, stands before his friends in the garage, notebook in hand, delivering a concise report — the tiredness in his eyes replaced by focused intensity. Use Image 2 as the exact background location. Medium shot, slight low angle. Morning sunlight from high window. {ST}",
))

EXT_CLIPS.append(raw("S08_F", "S08",
    "Тишина после доклада. Карим: «Может... это кто-то знакомый? Записку оставил?»",
    [K, L("garage")],
    f"The exact character in a black hoodie from Image 1, preserving identical facial features and proportions, breaks the silence in the garage, offering a hopeful alternative with uncertain body language — one hand raised palm-up, trying to find a reasonable explanation, but his own face doesn't believe it. Use Image 2 as the exact background location. Medium close-up, eye-level. Morning light, uncertain. {ST}",
    f"The exact character in a black hoodie from Image 1, preserving identical facial features and proportions, scratches the back of his head, suggesting a normal explanation, voice rising questioningly — even he knows it sounds weak. Use Image 2 as the exact background location. Medium shot, eye-level. Garage morning light. {ST}",
    f"The exact character in a black hoodie from Image 1, preserving identical facial features and proportions, shrugs with one shoulder, eyebrows up, trying to downplay the situation — but the attempt at optimism falters as he says it. Use Image 2 as the exact background location. Medium close-up, eye-level. Morning light, skeptical self-awareness. {ST}",
    f"The exact character in a black hoodie from Image 1, preserving identical facial features and proportions, offers a half-hearted alternative theory, hands spread in a 'maybe?' gesture, but the doubt in his own eyes undermines the suggestion. Use Image 2 as the exact background location. Medium shot, eye-level. Cool morning light. {ST}",
))

EXT_CLIPS.append(raw("S08_G", "S08",
    "Амин парирует: «В час ночи? Без фар? Не стучась?» Тишина.",
    [A, L("garage")],
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, counts off on three fingers in the garage — each point a nail in the coffin of the 'normal' explanation. Face calm but deadly serious. The silence that follows says everything. Use Image 2 as the exact background location. Medium close-up, eye-level. Sharp morning light. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, ticks off three damning facts on his fingers, voice flat and matter-of-fact, letting the logic speak for itself. Silence in the garage after. Use Image 2 as the exact background location. Medium shot, eye-level. Morning light cutting through the garage. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, raises three fingers one by one, each question rhetorical, each answer obvious. The garage is silent after he finishes. Nobody argues. Use Image 2 as the exact background location. Close-up on face and raised hand, eye-level. Bright morning light. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, speaks three short questions into the garage silence, each one shutting down any innocent explanation. The truth hangs in the air — this was a threat. Use Image 2 as the exact background location. Medium close-up, eye-level. Morning light, gravity of the moment. {ST}",
))

EXT_CLIPS.append(raw("S08_H", "S08",
    "Тако: «Я же говорил с самого начала—» Ая: «Тако.» Тако: «Что? Я говорил!»",
    [T, Y, L("garage")],
    f"First, the exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, puffs up in the garage, arms spread wide, the classic 'I told you so' posture, practically vibrating with vindication. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, gives him a single sharp look. He deflects: hands up, defiant. Use Image 3 as the exact background location. Medium two-shot, eye-level. Morning garage light. {ST}",
    f"First, the exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, springs to his feet, one finger pointed at everyone, mouth open mid-sentence about being right all along. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, cuts him short with a single calm word and a raised eyebrow. He sputters. Use Image 3 as the exact background location. Medium shot, eye-level. Morning light. {ST}",
    f"First, the exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, bounces on his toes, unable to contain his 'told you so' energy. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, silences him with a look — but he crosses his arms defiantly, not giving up the point. Use Image 3 as the exact background location. Medium close-up two-shot, eye-level. Morning light. {ST}",
    f"First, the exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, opens his mouth to gloat, arms wide. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, stops him with one word, calm authority in her expression. He closes his mouth, pouts, but can't suppress a vindicated smirk. Use Image 3 as the exact background location. Medium shot, eye-level. Garage morning light. {ST}",
))

EXT_CLIPS.append(raw("S08_I", "S08",
    "Ая: «Нужно поговорить с Джамилем. Прямо.» Серьёзная, решительная.",
    [Y, L("garage")],
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, stands in the garage, arms at her sides, chin slightly raised — speaking with quiet authority. This is not a suggestion, it's the next step. Composed and decisive. Use Image 2 as the exact background location. Medium close-up, eye-level. Morning light, determined atmosphere. {ST}",
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, faces the group, expression serious and clear, no hesitation — they need answers, and they need them from the source. Use Image 2 as the exact background location. Medium shot, slight low angle. Sharp morning light. {ST}",
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, speaks with calm certainty in the garage, eyes moving from face to face, ensuring everyone understands — it's time for a direct conversation. Use Image 2 as the exact background location. Medium close-up, eye-level. Morning garage light, resolve. {ST}",
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, makes her case in the garage with measured words and steady eyes — practical, direct, no drama. The right course of action is clear to her. Use Image 2 as the exact background location. Medium shot, eye-level. Morning light, quiet strength. {ST}",
))

EXT_CLIPS.append(raw("S08_J", "S08",
    "Амин: «Я пойду один. Тако — наблюдение.» Тако выпрямляется: «Принято, командир.»",
    [A, T, L("garage")],
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, assigns roles in the garage, pointing at himself, then at his youngest team member, calm command in his voice. Then, the exact character in a red-and-white striped shirt and red cap from Image 2, snaps to attention, back straight, chin up, accepting the mission with deadly seriousness. Use Image 3 as the exact background location. Medium two-shot, eye-level. Morning garage light. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, makes a decision, pointing to himself and then gesturing to the younger boy — each person has a role. Then, the exact character in a red-and-white striped shirt and red cap from Image 2, straightens instantly, a miniature soldier receiving orders, pride bursting from every pore. Use Image 3 as the exact background location. Medium shot, eye-level. Morning light, command moment. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, lays out the plan, one hand flat on the workbench — he goes alone, the kid watches from outside. Then, the exact character in a red-and-white striped shirt and red cap from Image 2, salutes with perfect seriousness, promoted to lookout duty. Use Image 3 as the exact background location. Medium shot, slight low angle. Bright morning light. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, speaks the plan, nodding at each person in turn. Then, the exact character in a red-and-white striped shirt and red cap from Image 2, squares his small shoulders, face absolutely serious — 'Acknowledged, Commander' written all over his posture. Use Image 3 as the exact background location. Medium two-shot, eye-level. Morning garage light. {ST}",
))

# ============================================================
# SCENE 9 — Additional clips (+9)
# ============================================================

EXT_CLIPS.append(raw("S09_H", "S09",
    "Establishing: двор Джамиля в беспорядке. Утренний свет на разбросанных бумагах.",
    [L("jamil_yard")],
    f"A courtyard in the morning light — papers scattered across stone ground, a wooden table with overturned items, wind rustling loose pages. Evidence of a night disturbance. Peaceful morning contrasting with chaos. Use Image 1 as the exact background location. Wide establishing shot, slightly high angle. Morning golden light on the disorder. {ST}",
    f"Morning sunlight reveals a courtyard in disarray — papers on the ground, a displaced crate, scattered notebooks. The calm morning light makes the disturbance feel more unsettling. Use Image 1 as the exact background location. Wide shot, eye-level. Warm morning light, disturbing contrast. {ST}",
    f"Early morning light floods a courtyard where papers lie scattered, a crate sits open against the wall, notebooks tossed about. A place that was orderly is now disrupted. Use Image 1 as the exact background location. Medium-wide shot, eye-level. Golden morning light on chaos. {ST}",
    f"A courtyard after a night intrusion — morning light illuminates scattered papers, an overturned box, displaced items. The calm dawn only heightens the wrongness of the scene. Use Image 1 as the exact background location. Wide shot, high angle. Morning light, aftermath. {ST}",
))

EXT_CLIPS.append(raw("S09_I", "S09",
    "Крупный план: смятая записка «УЕЗЖАЙ» в руке Джамиля.",
    [J],
    f"Close-up of weathered hands slowly unfolding a crumpled white paper, revealing a single word written in large aggressive black marker strokes — a threatening message. The hands are steady despite everything. {ST}",
    f"A pair of aged but strong hands flatten a crushed piece of paper on a table surface, one bold word in black marker visible — crude, threatening, unmistakable. The fingers press the creases flat with deliberate calm. {ST}",
    f"Close-up: wrinkled fingers smooth out a crumpled white sheet, revealing thick black marker letters — one word, a demand. The hands tremble slightly but do not release the paper. {ST}",
    f"Extreme close-up of a note being unfolded — creased white paper, one word scrawled in heavy black marker, filling the page with menace. Weathered hands hold it steady. {ST}",
))

EXT_CLIPS.append(raw("S09_J", "S09",
    "Джамиль опускает обрывки записки на стол. Лицо — упрямая, тихая сила.",
    [J, L("jamil_yard")],
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, places torn paper fragments on the courtyard table with deliberate calm, face showing quiet stubborn strength — like a tree root breaking concrete. Not anger. Principle. Use Image 2 as the exact background location. Close-up on face, eye-level. Warm daylight. {ST}",
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, lets the last torn pieces of paper fall from his fingers onto the table, chin slightly raised, eyes clear and resolved — this is a man who will not be moved. Use Image 2 as the exact background location. Medium close-up, eye-level. Bright day, defining moment. {ST}",
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, brushes torn paper scraps off his palms onto the table with finality, expression of quiet unbreakable will — done with fear, done with threats. Use Image 2 as the exact background location. Medium shot, eye-level. Morning light, resolution. {ST}",
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, looks down at the torn scraps of the threat on the table, then looks up — eyes clear, jaw set, the weariness replaced by iron determination. Use Image 2 as the exact background location. Close-up, slight low angle. Daylight, strength and dignity. {ST}",
))

EXT_CLIPS.append(raw("S09_K", "S09",
    "Амин смотрит на Джамиля с уважением. Понимает, что этот человек не сдастся.",
    [A, L("jamil_yard")],
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, stands in the courtyard watching the elderly man, expression shifting from concern to deep respect — witnessing real courage. Shoulders straightening unconsciously. Use Image 2 as the exact background location. Medium close-up, eye-level. Warm daylight. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, watches with quiet awe in the courtyard, recognizing the kind of strength that doesn't need volume — his own resolve hardening in response. Use Image 2 as the exact background location. Close-up, eye-level. Bright day, inspired expression. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, looks at the elderly man in the courtyard with new eyes — not just a mystery neighbor anymore, but someone worthy of real respect. Standing taller. Use Image 2 as the exact background location. Medium shot, eye-level. Morning light, moment of recognition. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, absorbs what he just witnessed in the courtyard, expression maturing — understanding that this is what real bravery looks like. Quiet, not loud. Use Image 2 as the exact background location. Close-up, eye-level. Warm daylight on a moved face. {ST}",
))

EXT_CLIPS.append(raw("S09_L", "S09",
    "Амин и Джамиль вместе собирают разбросанные бумаги во дворе.",
    [A, J, L("jamil_yard")],
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, kneels in the courtyard picking up scattered papers from the ground, careful with each page. Then, the exact character in a light shirt with rolled sleeves from Image 2, gathers pages from the other side, stacking them. Working together in companionable silence. Use Image 3 as the exact background location. Medium-wide shot, eye-level. Morning sunlight, quiet cooperation. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, bends down to collect papers blown across the courtyard stones. Then, the exact character in a light shirt with rolled sleeves from Image 2, accepts the gathered pages with a grateful nod, organizing them. Use Image 3 as the exact background location. Medium shot, eye-level. Warm morning light, beginning of partnership. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, carefully retrieves a scattered notebook from the ground. Then, the exact character in a light shirt with rolled sleeves from Image 2, takes it gently, checking the torn pages. Both working to restore order. Use Image 3 as the exact background location. Medium shot, eye-level. Morning light, cooperative moment. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, helps gather the wind-blown papers in the courtyard. Then, the exact character in a light shirt with rolled sleeves from Image 2, sorts them with practiced hands. An unspoken alliance forming. Use Image 3 as the exact background location. Medium-wide shot, slightly high angle. Warm morning sun. {ST}",
))

EXT_CLIPS.append(raw("S09_M", "S09",
    "Крупный план: обрывки записки «УЕЗЖАЙ» на столе. Ветер шевелит бумаги.",
    [L("jamil_yard")],
    f"Close-up of a courtyard table — torn white paper fragments with traces of black marker letters scattered among other papers, a breeze stirring the edges. The remnants of a threat, reduced to nothing. Use Image 1 as the exact background location. Close-up, slight overhead. Warm daylight, papers rustling. {ST}",
    f"Detail shot: torn paper scraps on a weathered table, fragments of thick black letters visible on each piece. Wind catches one and lifts it. The threat has been answered. Use Image 1 as the exact background location. Extreme close-up, slightly angled. Morning light, breeze moving the scraps. {ST}",
    f"A table in a courtyard with torn paper pieces — remnants of a threatening note — scattered among notebooks and maps. A gentle breeze plays with the scraps. Defiance in the small gesture. Use Image 1 as the exact background location. Close-up, overhead angle. Warm light on white paper fragments. {ST}",
    f"White paper fragments on a wooden courtyard table, black marker traces visible, wind beginning to scatter them further. The message is destroyed. The resolve remains. Use Image 1 as the exact background location. Close-up, eye-level across the table. Morning sunlight, symbolic destruction. {ST}",
))

EXT_CLIPS.append(raw("S09_N", "S09",
    "Титр: чёрный экран. Голос Тако шёпотом: «Тёмная машина. Она вернулась.»",
    [],
    f"A solid black screen — pure darkness, cinematic letterbox framing. Nothing visible. The end of Part 1. Tension in the void. {ST}",
    f"Complete blackness filling the frame — a dramatic end-of-episode moment. No light, no shapes. Just darkness and the implication of danger. {ST}",
    f"Black screen — total darkness, wide cinematic format. The moment before a revelation. The cliffhanger. {ST}",
    f"Pure black frame — cinematic darkness, the dramatic pause between parts of a story. Nothing visible. Everything implied. {ST}",
))

EXT_CLIPS.append(raw("S09_O", "S09",
    "Титр: «ПРОДОЛЖЕНИЕ СЛЕДУЕТ...» на чёрном фоне.",
    [],
    f"A dark cinematic frame with subtle warm light emerging from the edges — the feeling of a story pausing, not ending. Dramatic, hopeful despite the tension. {ST}",
    f"A nearly black frame with a faint warm glow at the bottom edge — atmospheric end-of-part shot, suspense meeting hope. Cinematic framing. {ST}",
    f"A dark frame with minimal ambient light — cinematic conclusion shot, the story suspended mid-beat. Tension and anticipation. {ST}",
    f"Deep black frame with the barest hint of dawn light at the horizon line — the pause between episodes, full of unresolved tension and promise. {ST}",
))

EXT_CLIPS.append(raw("S09_P", "S09",
    "Вид на дом Джамиля с улицы. Вечер. Тишина. Напряжение.",
    [L("jamil_house_front")],
    f"Exterior of an old house at dusk — closed shutters, locked gate, the last light of day fading on the stone walls. A house under siege. Silent. Waiting. Use Image 1 as the exact background location. Wide shot, eye-level. Dusk light, warm fading to cool, atmospheric tension. {ST}",
    f"The front of a modest old house as evening falls — everything closed and still, long shadows creeping across the facade. The house looks bunkered. Use Image 1 as the exact background location. Medium-wide shot, eye-level. Twilight, orange and purple sky. {ST}",
    f"An old house facade at dusk — door closed, gate shut, windows dark. The quiet of a street that knows something is wrong. Use Image 1 as the exact background location. Wide shot, slight low angle. Evening light fading, ominous calm. {ST}",
    f"Dusk settles on an old house exterior — silent, shuttered, waiting. The street is empty. The last sunlight touches the stone walls. Something is coming. Use Image 1 as the exact background location. Medium-wide shot, eye-level. Twilight atmosphere, tension. {ST}",
))

# ============================================================
# SCENE 10 — Additional clips (+8)
# ============================================================

EXT_CLIPS.append(raw("S10_G", "S10",
    "Амин: «Подземный город. Прямо под нашим городом.» Все в шоке.",
    [A, Y, K, L("garage")],
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, speaks in the garage with controlled intensity, hands spread wide — revealing something enormous. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, and the exact character in a black hoodie from Image 3, stare with identical expressions of stunned disbelief. Use Image 4 as the exact background location. Medium shot, eye-level. Morning garage light. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, delivers the revelation, voice low but powerful, watching the reaction. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, mouth slightly open in shock. Then, the exact character in a black hoodie from Image 3, frozen mid-lean. Use Image 4 as the exact background location. Medium-wide shot, eye-level. Morning light, bombshell moment. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, drops the biggest revelation yet in the garage — calm, factual, letting the information speak. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, blinks rapidly, processing. Then, the exact character in a black hoodie from Image 3, leans back in his seat. Use Image 4 as the exact background location. Medium shot, eye-level. Morning light. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, announces the discovery, watching each face change. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, puts a hand to her mouth. Then, the exact character in a black hoodie from Image 3, sits completely still. Use Image 4 as the exact background location. Medium shot, eye-level. Morning garage light, shock. {ST}",
))

EXT_CLIPS.append(raw("S10_H", "S10",
    "Карим: «И кто-то хочет это уничтожить?» Тишина.",
    [K, L("garage")],
    f"The exact character in a black hoodie from Image 1, preserving identical facial features and proportions, speaks the terrible implication aloud in the garage, voice hollow with the weight of it, face showing genuine distress at the thought of destruction. Silence follows. Use Image 2 as the exact background location. Medium close-up, eye-level. Morning light, grave realization. {ST}",
    f"The exact character in a black hoodie from Image 1, preserving identical facial features and proportions, voices what everyone is thinking, expression tight, the full scope of the threat sinking in — not just a neighbor in danger, but history itself at risk. Use Image 2 as the exact background location. Close-up, eye-level. Morning garage light, solemn. {ST}",
    f"The exact character in a black hoodie from Image 1, preserving identical facial features and proportions, asks the question that changes everything, his usual cool demeanor cracked by genuine horror at the idea. The garage falls silent. Use Image 2 as the exact background location. Medium close-up, eye-level. Morning light, heavy moment. {ST}",
    f"The exact character in a black hoodie from Image 1, preserving identical facial features and proportions, stares at his friend, the question hanging in the air like smoke, his face reflecting the enormity — five hundred years of history versus a shopping mall. Use Image 2 as the exact background location. Close-up, eye-level. Sharp morning light, silence. {ST}",
))

EXT_CLIPS.append(raw("S10_I", "S10",
    "Амин раздаёт задания: Ая — «Рассвет», Карим — номер машины, Тако — стройка.",
    [A, L("garage")],
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, stands in the garage, pointing to each person in turn as he assigns missions — organized, decisive, natural commander. Three different tasks, three different skills. Use Image 2 as the exact background location. Medium shot, slight low angle. Morning light, command presence. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, paces the garage, gesturing to each team member, distributing assignments based on each person's strength — a strategist deploying his assets. Use Image 2 as the exact background location. Medium-wide shot, eye-level. Bright morning light, mission briefing energy. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, ticks off assignments on his fingers, making eye contact with each person, voice calm and clear — everyone knows their job and why it matters. Use Image 2 as the exact background location. Medium shot, eye-level. Morning garage light, organized leadership. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, lays out the operation plan, each person getting their role, his confidence inspiring the team — this is how they fight back, with brains. Use Image 2 as the exact background location. Medium shot, slight low angle. Morning light, mission established. {ST}",
))

EXT_CLIPS.append(raw("S10_J", "S10",
    "Тако: «Полевая разведка. Стройка. Забор. Камеры.» Профессиональная серьёзность.",
    [T, L("garage")],
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, repeats his assignment in the garage with military precision, chin up, eyes focused — ticking off targets like a professional, completely in his element. Use Image 2 as the exact background location. Medium close-up, slight low angle. Morning light, absolute seriousness. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, nods crisply, then recites his mission parameters in the garage — construction site, perimeter, surveillance, security patterns — with zero trace of a joke. Use Image 2 as the exact background location. Medium shot, eye-level. Morning garage light. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, stands at attention in the garage, listing his reconnaissance targets with flat professional calm — fence, cameras, guard, schedule. Zero goofing. Pure focus. Use Image 2 as the exact background location. Medium close-up, eye-level. Morning light. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, accepts his assignment with a single professional nod, then runs through the checklist — perimeter, visual coverage, personnel — like a trained operative. Use Image 2 as the exact background location. Medium shot, slight low angle. Morning light, impressive professionalism. {ST}",
))

EXT_CLIPS.append(raw("S10_K", "S10",
    "Амин: «Только смотришь. Не лезешь.» Тако: «Обижаешь, командир.»",
    [A, T, L("garage")],
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, points firmly at the youngest member, expression stern but caring — setting the boundary. Then, the exact character in a red-and-white striped shirt and red cap from Image 2, places a hand on his heart, mock-offended but actually sincere, the professional who knows his limits. Use Image 3 as the exact background location. Medium two-shot, eye-level. Morning garage light. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, holds up a warning finger toward the boy, voice firm — observation only, no heroics. Then, the exact character in a red-and-white striped shirt and red cap from Image 2, rolls his eyes and huffs, arms crossed, but there's understanding beneath the theatrics. Use Image 3 as the exact background location. Medium shot, eye-level. Morning light, affectionate dynamic. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, makes the rule clear with a level gaze and pointed finger. Then, the exact character in a red-and-white striped shirt and red cap from Image 2, straightens indignantly, putting his cap on more firmly, but nods — the commander's word is law. Use Image 3 as the exact background location. Medium close-up two-shot, eye-level. Morning light. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, sets the boundary with firm eye contact. Then, the exact character in a red-and-white striped shirt and red cap from Image 2, scoffs quietly but accepts — deep down he knows the rules keep them all safe. Use Image 3 as the exact background location. Medium two-shot, eye-level. Morning garage light. {ST}",
))

EXT_CLIPS.append(raw("S10_L", "S10",
    "Ая: «Подожди. Подземный город?» Глаза широко. Смесь восторга и тревоги.",
    [Y, L("garage")],
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, leans forward in the garage, eyes wide, voice rising with disbelief and excitement — the words 'underground city' still sinking in, face showing the thrill of discovery mixed with fear. Use Image 2 as the exact background location. Medium close-up, eye-level. Morning light on her amazed face. {ST}",
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, pauses mid-thought in the garage, hands frozen, the scale of the revelation hitting her — wonder and worry fighting for control of her expression. Use Image 2 as the exact background location. Close-up, eye-level. Morning garage light, emotional mix. {ST}",
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, grips the edge of the workbench, eyes shining, mouth slightly open — trying to process the idea that an ancient city lies beneath their feet. Use Image 2 as the exact background location. Medium close-up, eye-level. Morning light, awe. {ST}",
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, sits back in the garage, one hand over her heart, face showing the peculiar mix of 'this is incredible' and 'this is dangerous'. Use Image 2 as the exact background location. Medium shot, eye-level. Morning light, dawning realization. {ST}",
))

EXT_CLIPS.append(raw("S10_M", "S10",
    "Крупный план карты города на стене гаража. Амин указывает на старый квартал.",
    [A, L("garage")],
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, stands at the wall map in the garage, finger pointing at a specific area — the old quarter, the construction site. Connecting dots on the map, showing the geography of the conspiracy. Use Image 2 as the exact background location. Medium shot, eye-level. Morning light on the map, planning session. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, traces a route on the city map pinned to the garage wall, circling two areas — the old quarter and the construction site — explaining how they connect. Use Image 2 as the exact background location. Close-up on hand and map, slight angle. Morning light illuminating the map. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, taps the wall map decisively, showing the team where the underground city lies, where the construction threatens it, where the second entrance might be. Use Image 2 as the exact background location. Medium close-up, over-shoulder toward map. Morning garage light. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, draws invisible connections on the map with his finger — from the construction site to the old quarter to the mosque. The geography of a five-hundred-year-old secret. Use Image 2 as the exact background location. Medium shot, eye-level. Morning light on the map details. {ST}",
))

EXT_CLIPS.append(raw("S10_N", "S10",
    "Все четверо у карты. Серьёзные лица. Планирование операции.",
    [A, K, T, L("garage")],
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, stands at the wall map. Then, the exact character in a black hoodie from Image 2, studies the map from the side. Then, the exact character in a red-and-white striped shirt and red cap from Image 3, cranes his neck to see. All focused on the map, planning their operation. Use Image 4 as the exact background location. Medium-wide shot, eye-level. Morning garage light, mission planning. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, points at the map. Then, the exact character in a black hoodie from Image 2, nods, arms crossed. Then, the exact character in a red-and-white striped shirt and red cap from Image 3, stands on tiptoes to see better. Three young investigators, one mission. Use Image 4 as the exact background location. Medium shot, slight high angle. Morning light. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, leads the briefing at the map. Then, the exact character in a black hoodie from Image 2, leans in attentively. Then, the exact character in a red-and-white striped shirt and red cap from Image 3, memorizes his section with intense focus. A team united. Use Image 4 as the exact background location. Medium-wide shot, eye-level. Morning garage atmosphere. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, traces the plan on the map. Then, the exact character in a black hoodie from Image 2, points to a detail. Then, the exact character in a red-and-white striped shirt and red cap from Image 3, gives a thumbs up. Strategy session complete. Use Image 4 as the exact background location. Medium shot, eye-level. Morning light, teamwork. {ST}",
))

# ============================================================
# SCENE 11 — Parallel montage — Additional clips (+11)
# ============================================================

EXT_CLIPS.append(raw("S11_F", "S11",
    "Ая в библиотеке: палец скользит по столбцам газеты. Останавливается.",
    [Y, L("library")],
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, sits at a library table, a stack of bound newspaper volumes before her, finger tracing down a column of text — then stopping, pressing the page flat. Something found. Use Image 2 as the exact background location. Medium close-up, eye-level. Quiet library light, green lamp glow. {ST}",
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, leans over an open newspaper archive in the library, scanning methodically, one finger running along the print — then freezing on a line. Eyes widening. Use Image 2 as the exact background location. Close-up, slight overhead on the page. Soft library daylight. {ST}",
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, turns pages of bound newspapers in a quiet library, scanning efficiently — and then her finger stops, taps a specific article twice. Found it. Use Image 2 as the exact background location. Medium shot, eye-level. Warm library atmosphere, green desk lamps. {ST}",
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, sits surrounded by newspaper stacks in the library, finger sliding down columns of small print — suddenly stopping, leaning closer, reading intently. Discovery. Use Image 2 as the exact background location. Medium close-up, eye-level. Library light, focused research. {ST}",
))

EXT_CLIPS.append(raw("S11_G", "S11",
    "Крупный план: газетная заметка о компании «Рассвет» и разрешении на строительство.",
    [L("library")],
    f"Close-up of a newspaper page — a short article visible, next to a classified section. A headline about construction permits, a company name mentioned in the text. A finger underlines a key phrase. Old newsprint, slightly yellowed. Use Image 1 as the exact background location. Extreme close-up, slight angle. Green desk lamp illumination on the page. {ST}",
    f"A finger points to a newspaper article in a bound volume — a brief notice about a construction company receiving building permits in the old quarter. The text is small but the implications are enormous. Use Image 1 as the exact background location. Close-up, overhead. Warm library lighting on newsprint. {ST}",
    f"An old newspaper article under a green desk lamp — a short column about construction permits, a company name, a location. The kind of small notice that hides big secrets. Use Image 1 as the exact background location. Close-up, angled. Library atmosphere, green lamp glow on text. {ST}",
    f"Detail shot of a newspaper column — an article about commercial development in the old quarter, a company named in the text. Old paper, tiny type, huge consequences. Use Image 1 as the exact background location. Extreme close-up. Warm desk lamp illuminating the fine print. {ST}",
))

EXT_CLIPS.append(raw("S11_H", "S11",
    "Ая записывает имя «Рашид Камаль» в блокнот. Подчёркивает дважды.",
    [Y, L("library")],
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, writes carefully in a small notebook at the library table, then draws two firm lines under a name — deliberate, emphatic. A suspect identified. Use Image 2 as the exact background location. Close-up on hands writing, eye-level. Green library lamp light. {ST}",
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, finishes writing in her notebook and underscores a name twice with her pen, pressing hard — this name matters. Use Image 2 as the exact background location. Close-up on notebook and pen, slight overhead. Library lamp glow. {ST}",
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, writes in her notebook with precise handwriting, then drags her pen under a name — once, twice — looking at it with narrowed investigator's eyes. Use Image 2 as the exact background location. Medium close-up, eye-level. Library interior, scholarly determination. {ST}",
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, closes the newspaper volume, opens her notebook, writes a name, and underlines it firmly twice. Evidence collected. Lead identified. Use Image 2 as the exact background location. Medium shot, eye-level. Quiet library atmosphere. {ST}",
))

EXT_CLIPS.append(raw("S11_I", "S11",
    "Карим у автомойки. Солнце, вода на бетоне. Разговаривает со старшеклассником.",
    [K, L("carwash")],
    f"The exact character in a black hoodie from Image 1, preserving identical facial features and proportions, stands at a car wash, talking casually with an older teen in a wet apron, showing a piece of paper — the sunlight bouncing off wet concrete around them. Use Image 2 as the exact background location. Medium shot, eye-level. Bright midday sun, wet reflections. {ST}",
    f"The exact character in a black hoodie from Image 1, preserving identical facial features and proportions, leans against the car wash wall, talking to a worker, holding up a paper with a license number, casual and non-threatening — just a kid asking questions. Use Image 2 as the exact background location. Medium-wide shot, eye-level. Harsh afternoon sun, water on concrete. {ST}",
    f"The exact character in a black hoodie from Image 1, preserving identical facial features and proportions, holds a paper scrap toward a car wash attendant, questioning, nodding as he gets information — the attendant gestures while drying a wheel. Use Image 2 as the exact background location. Medium shot, eye-level. Bright sun, water puddles reflecting light. {ST}",
    f"The exact character in a black hoodie from Image 1, preserving identical facial features and proportions, has a low-key conversation at the car wash, hands in pockets except for the paper he shows briefly — extracting information without drawing attention. Use Image 2 as the exact background location. Medium shot, slight low angle. Midday sun, wet ground sparkle. {ST}",
))

EXT_CLIPS.append(raw("S11_J", "S11",
    "Карим записывает информацию. «Костюм. Наличные. Тихий голос.»",
    [K, L("carwash")],
    f"The exact character in a black hoodie from Image 1, preserving identical facial features and proportions, writes in a small notebook at the car wash, pen moving quickly, glancing up between notes to make sure no one watches — recording what the worker told him. Use Image 2 as the exact background location. Medium close-up, eye-level. Bright afternoon sun, undercover research. {ST}",
    f"The exact character in a black hoodie from Image 1, preserving identical facial features and proportions, leans against a wall at the car wash, scribbling notes on a piece of paper balanced on his knee — suit, cash, quiet voice — building a profile. Use Image 2 as the exact background location. Medium shot, eye-level. Afternoon sun, productive fieldwork. {ST}",
    f"The exact character in a black hoodie from Image 1, preserving identical facial features and proportions, jots down key details at the car wash, the pen scratching quickly — each piece of information another thread in the investigation. Use Image 2 as the exact background location. Close-up on hands and paper, eye-level. Bright daylight. {ST}",
    f"The exact character in a black hoodie from Image 1, preserving identical facial features and proportions, finishes writing at the car wash, reviews his notes, nods to himself — useful intel gathered. Folds the paper and pockets it. Use Image 2 as the exact background location. Medium shot, eye-level. Afternoon sun, mission accomplished. {ST}",
))

EXT_CLIPS.append(raw("S11_K", "S11",
    "Тако идёт мимо стройки. Бросает мяч — обычный мальчик на прогулке. Глаза сканируют.",
    [T, L("strojka")],
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, walks casually past a construction site fence, bouncing a small ball ahead of him — the picture of an innocent child at play. But his eyes are scanning. Everything. Use Image 2 as the exact background location. Medium-wide shot, eye-level. Afternoon sun, covert observation. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, strolls along a concrete fence by a construction site, kicking a ball lazily, looking like any bored seven-year-old — while his eyes map every camera, every gap, every detail. Use Image 2 as the exact background location. Medium shot, eye-level. Bright day, disguised surveillance. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, ambles past a tall concrete fence with a ball, the perfect cover — nobody suspects a child at play. His eyes, though, miss nothing: the camera angle, the guard booth, the weak point in the fence. Use Image 2 as the exact background location. Medium-wide shot, eye-level. Afternoon sunlight, clever cover. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, bounces his ball along the sidewalk past the construction site, head seemingly focused on play — but glancing sideways at the fence, the gate, the security camera, cataloguing everything. Use Image 2 as the exact background location. Medium shot, slight low angle. Bright day, deceptive innocence. {ST}",
))

EXT_CLIPS.append(raw("S11_L", "S11",
    "Тако бормочет, шевеля губами: анализирует камеры, забор, слепые зоны.",
    [T, L("strojka")],
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, walks slowly past the construction fence, lips barely moving, whispering to himself — counting, measuring, memorizing. Eyes tracking upward to a camera on a pole. Use Image 2 as the exact background location. Close-up, profile, walking. Afternoon light, lip-reading impossible but lips definitely moving. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, passes the construction site for a second time, ball under his arm, head slightly tilted as he counts steps along the fence — lips moving with barely audible analysis. Use Image 2 as the exact background location. Medium close-up, three-quarter view. Bright afternoon, intense concentration behind the casual mask. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, stands near the fence corner, bouncing the ball absently, lips moving as he catalogs observations — one camera, blind spot right, fence gap at third post. Professional-level reconnaissance. Use Image 2 as the exact background location. Medium shot, eye-level. Afternoon sun, focused operative. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, walks past the guard booth entrance, eyes sliding to the side, lips counting — the guard's tea schedule, the camera rotation, the vulnerable section. All recorded. Use Image 2 as the exact background location. Medium close-up, walking profile. Afternoon light. {ST}",
))

EXT_CLIPS.append(raw("S11_M", "S11",
    "Охранник выглядывает из будки. Тако мгновенно начинает пинать мяч, изображая игру.",
    [T, L("strojka")],
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, immediately pivots from surveillance mode to full kid-play mode, kicking the ball energetically, face suddenly bright and carefree — the instant transition of a born operative. Use Image 2 as the exact background location. Medium shot, eye-level. Afternoon sun, flawless cover. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, starts dribbling the ball with exaggerated enthusiasm the instant he senses attention — jumping, spinning, every inch the playful child with zero interest in anything but his ball. Use Image 2 as the exact background location. Medium-wide shot, eye-level. Bright afternoon, perfect disguise. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, switches instantly to playing, kicking the ball against the wall, laughing to himself — the transition from spy to kid so seamless it's art. The guard loses interest. Use Image 2 as the exact background location. Medium shot, eye-level. Afternoon light, masterful deception. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, kicks the ball high in the air and catches it, giggling — a completely ordinary child playing. The serious operative vanished between one heartbeat and the next. Use Image 2 as the exact background location. Medium shot, slight low angle. Afternoon sun, innocent play. {ST}",
))

EXT_CLIPS.append(raw("S11_N", "S11",
    "Ая в библиотеке ищет фотографию Рашида Камаля — ничего. «Призрак.»",
    [Y, L("library")],
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, flips through another newspaper volume in the library, searching for a face that doesn't exist — frustration growing, each empty page confirming the absence. A ghost. Use Image 2 as the exact background location. Medium close-up, eye-level. Library light, frustrated determination. {ST}",
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, pushes back from the library table, surrounded by open newspaper volumes, all yielding nothing — no photo, no face. Just a name on paper. Her expression is troubled but thoughtful. Use Image 2 as the exact background location. Medium shot, eye-level. Library atmosphere, dead end. {ST}",
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, closes the last bound volume with a soft thump, looks at her notes — one name, zero photographs, zero personal information. A man who exists only on paper. Use Image 2 as the exact background location. Medium close-up, eye-level. Quiet library light, disturbing absence. {ST}",
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, stares at her notebook in the library — a name written and underlined, but nothing else. No picture, no interview, no trace. She taps her pen on the paper, thinking hard. Use Image 2 as the exact background location. Close-up on notebook and thoughtful face, eye-level. Library lamp glow. {ST}",
))

EXT_CLIPS.append(raw("S11_O", "S11",
    "Закат. Все три линии расследования заканчиваются. Тако, Карим и Ая в пути.",
    [L("house_front")],
    f"A residential street at sunset — golden light painting the houses, long shadows stretching across the road. Three different paths converging homeward. The day's investigation complete. Use Image 1 as the exact background location. Wide establishing shot, eye-level. Golden sunset light, end of a productive day. {ST}",
    f"Sunset on a quiet neighborhood street — warm orange light on stone walls, purple shadows. The feeling of separate missions ending, information gathered, answers found. Time to reconvene. Use Image 1 as the exact background location. Wide shot, eye-level. Beautiful sunset, productive day ending. {ST}",
    f"A street at golden hour — the sun low, houses glowing warm, the end of a day of investigation. Peace on the surface, secrets underneath. Use Image 1 as the exact background location. Medium-wide establishing shot, eye-level. Rich sunset colors. {ST}",
    f"Evening settles on the residential street — golden light fading to purple, the quiet of a day's work done. Three investigations complete. Time to compare notes. Use Image 1 as the exact background location. Wide shot, eye-level. Sunset atmosphere, transitional moment. {ST}",
))

EXT_CLIPS.append(raw("S11_P", "S11",
    "Смена кадров: быстрый монтаж — руки листают газету, ведро с водой, мяч у забора.",
    [],
    f"A collage of investigative moments: fingers on newspaper text, water splashing on car wash concrete, a ball rolling past a concrete fence. Quick cuts of the parallel investigation. Bright afternoon light across all shots. {ST}",
    f"Quick montage details: a pen underlining text in a newspaper, soapy water running on concrete, a red ball bouncing near a grey fence. Three investigations, one mission. Daylight, fast rhythm. {ST}",
    f"Rapid visual summary: finger on newsprint, car wash spray, a ball's shadow on a concrete wall. Each element representing one branch of the investigation. Afternoon energy. {ST}",
    f"Montage elements: newspaper columns, wet concrete shine, ball against fence. The visual rhythm of three parallel stories happening simultaneously across the city. Bright day, dynamic. {ST}",
))

# ============================================================
# SCENE 12 — Additional clips (+9)
# ============================================================

EXT_CLIPS.append(raw("S12_F", "S12",
    "Тако докладывает про стройку: забор, щель, камера, слепая зона, охранник, чай в 16:00.",
    [T, L("garage")],
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, stands in the garage delivering his surveillance report with flat professional calm — ticking off fence height, camera coverage, blind spots, guard habits — three days of observations distilled into precise data. Use Image 2 as the exact background location. Medium shot, slight low angle. Evening garage light, impressive professionalism. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, presents his findings in the garage like a military briefing — fence specs, security gaps, guard schedule, all memorized and delivered without notes. Everyone stares. Use Image 2 as the exact background location. Medium close-up, eye-level. Evening light, stunned respect. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, recites his reconnaissance data in the garage — every detail of the construction site's security, precise and complete. The room is silent with respect. Use Image 2 as the exact background location. Medium shot, eye-level. Evening garage light, operational briefing. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, delivers a comprehensive site analysis in the garage — perimeter, surveillance, personnel, timing — with the confidence of someone who has done this three days running and knows every detail cold. Use Image 2 as the exact background location. Medium shot, slight low angle. Evening light, commanding delivery. {ST}",
))

EXT_CLIPS.append(raw("S12_G", "S12",
    "Все смотрят на Тако с удивлением. Карим: «Три дня? Когда ты успел?»",
    [K, T, L("garage")],
    f"First, the exact character in a black hoodie from Image 1, preserving identical facial features and proportions, stares at the youngest member with genuine astonishment in the garage, mouth slightly open — he never expected this level of detail. Then, the exact character in a red-and-white striped shirt and red cap from Image 2, stands with arms folded, chin raised — of course he delivered. Use Image 3 as the exact background location. Medium two-shot, eye-level. Evening garage light, surprise and pride. {ST}",
    f"First, the exact character in a black hoodie from Image 1, preserving identical facial features and proportions, turns to the boy with disbelief mixed with admiration — 'when did you have time for all this?' Then, the exact character in a red-and-white striped shirt and red cap from Image 2, shrugs as if it's the most natural thing in the world. Use Image 3 as the exact background location. Medium shot, eye-level. Evening light, earned respect moment. {ST}",
    f"First, the exact character in a black hoodie from Image 1, preserving identical facial features and proportions, shakes his head slowly in the garage, impressed despite himself. Then, the exact character in a red-and-white striped shirt and red cap from Image 2, adjusts his cap with casual confidence — just doing his job. Use Image 3 as the exact background location. Medium close-up, eye-level. Evening light. {ST}",
    f"First, the exact character in a black hoodie from Image 1, preserving identical facial features and proportions, asks with raised eyebrows, leaning toward the boy. Then, the exact character in a red-and-white striped shirt and red cap from Image 2, meets his gaze coolly — 'I'm a serious person, Karim.' Use Image 3 as the exact background location. Medium two-shot, eye-level. Evening garage atmosphere. {ST}",
))

EXT_CLIPS.append(raw("S12_H", "S12",
    "Тако: «Я серьёзный человек, Карим.» Даже Ая кивает уважительно.",
    [T, Y, L("garage")],
    f"First, the exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, draws himself up to full height in the garage, expression of absolute dignity — not a joke, not a boast, a statement of fact. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, gives a small, genuine nod of respect. Use Image 3 as the exact background location. Medium shot, eye-level. Evening light, a big moment for a small person. {ST}",
    f"First, the exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, speaks with quiet certainty in the garage, all playfulness gone — replaced by the real person underneath. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, acknowledges him with a nod that says 'you earned this.' Use Image 3 as the exact background location. Medium close-up, eye-level. Evening light, genuine respect. {ST}",
    f"First, the exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, stands firm, not seeking approval but stating truth. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, tips her head slightly — the hardest person to impress, giving quiet recognition. Use Image 3 as the exact background location. Medium shot, eye-level. Warm evening light. {ST}",
    f"First, the exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, meets all eyes steadily in the garage. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, nods once — brief, sincere, the most meaningful approval possible. Use Image 3 as the exact background location. Medium two-shot, eye-level. Evening garage light, significant moment. {ST}",
))

EXT_CLIPS.append(raw("S12_I", "S12",
    "Тако показывает план стройки жестом «ребром ладони по горлу». Секунда тишины. Все смеются.",
    [T, A, K, L("garage")],
    f"First, the exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, slowly draws the edge of his hand across his throat with a dead-serious stone face — the classic 'eliminate the guard' gesture. Then, the exact character in a grey hoodie from Image 2, bites his lip trying not to laugh. Then, the exact character in a black hoodie from Image 3, snorts first. Use Image 4 as the exact background location. Medium shot, eye-level. Evening light, comic timing. {ST}",
    f"First, the exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, makes the throat-slash gesture with absolute gravity, not blinking, playing it completely straight. One second of stunned silence. Then, the exact character in a grey hoodie from Image 2, covers his mouth. Then, the exact character in a black hoodie from Image 3, bursts out laughing. Use Image 4 as the exact background location. Medium shot, eye-level. Evening light, perfect comedic beat. {ST}",
    f"First, the exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, delivers the hand-across-throat gesture like a miniature action hero. Dead silence for one beat. Then everyone breaks — the exact character in a grey hoodie from Image 2, doubles over. The exact character in a black hoodie from Image 3, clutches his stomach. Use Image 4 as the exact background location. Medium-wide shot, eye-level. Evening light, laughter erupting. {ST}",
    f"First, the exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, pantomimes 'neutralizing' the guard with lethal seriousness. A frozen moment. Then the garage explodes with laughter — the exact character in a grey hoodie from Image 2, and the exact character in a black hoodie from Image 3, unable to hold it together. Use Image 4 as the exact background location. Medium shot, eye-level. Evening light, pure comedy. {ST}",
))

EXT_CLIPS.append(raw("S12_J", "S12",
    "Амин (давясь смехом): «Мы не устраняем охранников.» Тако бурчит.",
    [A, T, L("garage")],
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, tries to be serious but can barely talk through suppressed laughter, one hand up, tears in eyes, explaining the rules of engagement. Then, the exact character in a red-and-white striped shirt and red cap from Image 2, pouts with arms crossed, genuinely put out that his plan was dismissed. Use Image 3 as the exact background location. Medium two-shot, eye-level. Evening light, aftermath of laughter. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, composes himself with difficulty, wiping his eyes, explaining patiently through residual giggles that they don't eliminate guards. Then, the exact character in a red-and-white striped shirt and red cap from Image 2, huffs and mutters, turning away — unappreciated genius. Use Image 3 as the exact background location. Medium shot, eye-level. Evening light, comic warmth. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, bites his lip hard, trying to regain commander composure in the garage, a laugh still escaping. Then, the exact character in a red-and-white striped shirt and red cap from Image 2, grumbles under his breath, bottom lip jutting — nobody values professionals. Use Image 3 as the exact background location. Medium close-up, eye-level. Evening light, affectionate comedy. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, clears his throat, swallows a laugh, and delivers the correction with as much gravity as he can manage. Then, the exact character in a red-and-white striped shirt and red cap from Image 2, sulks dramatically, arms tight, chin down — filing this under 'they'll regret this.' Use Image 3 as the exact background location. Medium two-shot, eye-level. Evening light. {ST}",
))

EXT_CLIPS.append(raw("S12_K", "S12",
    "Ая серьёзно: «Нам нужно обсудить кое-что.» Все поворачиваются.",
    [Y, L("garage")],
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, speaks in the garage after the laughter dies, voice cutting through like cold water — the mood shifts instantly. She has something important, and the room knows it. Use Image 2 as the exact background location. Medium close-up, eye-level. Evening light, sudden gravity. {ST}",
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, waits for the laughter to fade, then speaks two sentences that silence the room. Everyone turns. The fun is over. Use Image 2 as the exact background location. Medium shot, eye-level. Evening garage light, dramatic shift. {ST}",
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, breaks through the post-joke atmosphere with a serious tone, her expression unchanged by the humor — she's been thinking about something important. Use Image 2 as the exact background location. Medium close-up, eye-level. Evening light, pivotal moment. {ST}",
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, interrupts the lightness with calm authority — two words, and the garage goes quiet. She has the floor. Use Image 2 as the exact background location. Close-up, eye-level. Evening light, command of the room. {ST}",
))

EXT_CLIPS.append(raw("S12_L", "S12",
    "Ая: «Мы знаем его 4 дня. Не проверили ни одного слова. Мы должны быть умнее.»",
    [Y, L("garage")],
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, speaks in the garage with measured precision — not accusatory, not cold, just clear-eyed. The counterbalance to enthusiasm. The voice of 'what if we're wrong?' Use Image 2 as the exact background location. Medium close-up, eye-level. Evening light, intellectual honesty. {ST}",
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, makes her case carefully in the garage, hands folded, eyes moving from face to face — she respects Jamil, but trust must be earned, not assumed. Use Image 2 as the exact background location. Medium shot, eye-level. Evening garage light, voice of reason. {ST}",
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, lays out her concern with analytical calm — four days, one story, zero verification. Likable doesn't mean trustworthy. Smart means checking. Use Image 2 as the exact background location. Medium close-up, eye-level. Evening light, uncomfortable truth. {ST}",
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, presents the uncomfortable question with gentle firmness — 'people are more complex than good and bad.' The group needs to hear this. Use Image 2 as the exact background location. Medium shot, eye-level. Evening light, mature perspective. {ST}",
))

EXT_CLIPS.append(raw("S12_M", "S12",
    "Амин: «Согласен. Помогаем — и проверяем. Одновременно.»",
    [A, Y, L("garage")],
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, nods slowly in the garage, accepting his sister's wisdom — not defensive, genuinely considering. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, meets his eyes with satisfaction — he listened. Use Image 3 as the exact background location. Medium two-shot, eye-level. Evening light, mature agreement. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, speaks carefully, integrating her caution into the plan — help and verify simultaneously. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, nods — the right answer. Use Image 3 as the exact background location. Medium shot, eye-level. Evening garage light, wisdom accepted. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, agrees in the garage with his sister's caution, the plan evolving — trust but verify, an upgrade to the strategy. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, relaxes slightly. Use Image 3 as the exact background location. Medium close-up, eye-level. Evening light, balanced approach. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, adds verification to the mission plan, nodding at his sister — she's right and he knows it. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, gives the smallest satisfied smile. Use Image 3 as the exact background location. Medium two-shot, eye-level. Evening light. {ST}",
))

EXT_CLIPS.append(raw("S12_N", "S12",
    "Амин: «Я попрошу его показать документы. Фотографии экспедиции. Настоящий учёный покажет.»",
    [A, L("garage")],
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, speaks with renewed determination in the garage — the plan is refined, the test is set. If the old man is real, he'll prove it. Confidence and caution balanced. Use Image 2 as the exact background location. Medium close-up, eye-level. Evening light, decisive. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, outlines the verification step in the garage — a simple, elegant test. A real scientist shares evidence. A fraud avoids it. One meeting will tell. Use Image 2 as the exact background location. Medium shot, eye-level. Evening garage light, strategic clarity. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, concludes the planning session with the verification strategy — direct, respectful, conclusive. His face shows the maturity of a leader who listens to his team. Use Image 2 as the exact background location. Medium close-up, eye-level. Evening light, plan complete. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, sets the final piece of the plan in place — ask for proof. If the answer is yes, they're all in. If not, they know. Simple. Use Image 2 as the exact background location. Medium shot, eye-level. Evening garage light, resolution. {ST}",
))

# ============================================================
# SCENE 13 — Jamil shows evidence (+10)
# ============================================================

EXT_CLIPS.append(raw("S13_G", "S13",
    "Establishing: Джамиль за столом во дворе. Ящики закрыты. Записи сложены стопкой. Ждал.",
    [J, L("jamil_yard")],
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, sits at the courtyard table, notes stacked neatly before him, crates closed, posture of someone who made a decision in the night — ready to share everything. Use Image 2 as the exact background location. Medium-wide shot, eye-level. Morning light, quiet resolve. {ST}",
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, waits at the courtyard table, papers organized, a notebook positioned carefully — the scene is set for a revelation, calm and deliberate. Use Image 2 as the exact background location. Medium shot, eye-level. Warm morning sunlight, expectant atmosphere. {ST}",
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, sits composed in the courtyard, everything tidy — crates shut, papers stacked — the opposite of yesterday's chaos. He was up all night preparing. Use Image 2 as the exact background location. Medium-wide establishing shot, eye-level. Morning light, order restored. {ST}",
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, waits at the table, hands resting on a closed notebook, face calm — a man who has decided to trust, to share what he's guarded for twelve years. Use Image 2 as the exact background location. Medium shot, eye-level. Morning sun, quiet dignity. {ST}",
))

EXT_CLIPS.append(raw("S13_H", "S13",
    "Джамиль открывает тетрадь — осторожно, как Коран. Старые чертежи, цифры, наброски.",
    [J, L("jamil_yard")],
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, opens a worn cloth-covered notebook with reverent care — pages of hand-drawn diagrams, columns of numbers, cross-section sketches emerge. A life's work in one book. Use Image 2 as the exact background location. Close-up on hands and notebook, eye-level. Morning light on yellowed pages. {ST}",
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, gently lifts the cover of a thick notebook, fingers delicate on the aged paper — revealing meticulous hand-drawn maps, measurement columns, geological sketches. Use Image 2 as the exact background location. Close-up, slight overhead. Warm morning sun illuminating the pages. {ST}",
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, handles the notebook like a sacred text — opening to pages dense with precise handwritten data, careful drawings, coordinates. Twelve years of silence, now open. Use Image 2 as the exact background location. Close-up on notebook pages, eye-level. Morning light, revelation. {ST}",
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, turns the notebook pages slowly, each one a window into years of field research — measurements, sketches, notations in neat script. Use Image 2 as the exact background location. Close-up, overhead angle. Warm morning light on the evidence. {ST}",
))

EXT_CLIPS.append(raw("S13_I", "S13",
    "Крупный план: чёрно-белые фотографии. Тёмный проход, арочный свод, ниши в стенах.",
    [L("jamil_yard")],
    f"Close-up of grainy black-and-white photographs spread on a courtyard table — a dark arched passage carved from stone, walls with tool marks, small niches for oil lamps at regular intervals. Ancient underground architecture. {ST}",
    f"Black-and-white photographs on a sunlit table — images of an underground space: arched stone ceiling, carved niches in walls, stone steps worn smooth by centuries of feet. Proof of something extraordinary. {ST}",
    f"Grainy monochrome prints spread on a wooden table in daylight — underground passages, stone archways, rows of small wall niches, rough-hewn steps descending into darkness. Evidence of a hidden world. {ST}",
    f"Old photographs in morning light — showing carved stone corridors, arched ceilings, ventilation shafts, sleeping platforms — an underground city documented twelve years ago and preserved in these images. {ST}",
))

EXT_CLIPS.append(raw("S13_J", "S13",
    "Крупный план: фото надписи на стене — арабская вязь, вырезанная в камне.",
    [L("jamil_yard")],
    f"A photograph held in morning light — showing a stone wall with Arabic calligraphy carved deep into the surface, large letters meant to be read by lamplight. Five hundred years of faith preserved in stone. {ST}",
    f"Close-up of a black-and-white photograph — an ancient inscription carved into underground stone, Arabic script, rough but legible letters, deeply cut to last centuries. A message from the past. {ST}",
    f"A grainy photograph showing carved Arabic text on a stone wall — deep-cut calligraphy, each letter deliberate, designed to survive. An ancient prayer etched into rock. {ST}",
    f"Detail of a photograph: Arabic calligraphy carved into stone, large and clear despite centuries — a prayer, a plea, a bridge across five hundred years. Photographed underground by flashlight. {ST}",
))

EXT_CLIPS.append(raw("S13_K", "S13",
    "Амин читает надпись: «Бисмиллях ар-Рахман ар-Рахим. Мы укрылись здесь от несправедливости.»",
    [A, J, L("jamil_yard")],
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, leans over a photograph in the courtyard, reading the ancient inscription aloud, voice hushed with awe — the words hitting him like physical impact. Then, the exact character in a light shirt with rolled sleeves from Image 2, watches the boy's reaction, seeing his own wonder reflected. Use Image 3 as the exact background location. Medium close-up, eye-level. Morning light, sacred moment. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, reads the translation of the inscription, voice barely above a whisper, eyes shining — connecting across centuries with the people who wrote these words. Then, the exact character in a light shirt with rolled sleeves from Image 2, nods slowly. Use Image 3 as the exact background location. Close-up on faces, eye-level. Warm morning light, emotional. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, speaks the ancient prayer softly in the courtyard, the words heavy with meaning, expression transforming from curiosity to reverence. Then, the exact character in a light shirt with rolled sleeves from Image 2, closes his eyes briefly, moved. Use Image 3 as the exact background location. Medium close-up, eye-level. Morning sun, transcendent moment. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, reads the words carved five centuries ago, voice dropping to a whisper at the end, visibly affected. Then, the exact character in a light shirt with rolled sleeves from Image 2, watches with glistening eyes. Use Image 3 as the exact background location. Close-up, eye-level. Morning light, emotional connection. {ST}",
))

EXT_CLIPS.append(raw("S13_L", "S13",
    "Тишина после надписи. Ветер. Амин: «500 лет... и они просили за нас.»",
    [A, L("jamil_yard")],
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, sits in the courtyard in the silence that follows, face working with emotion — the weight of five hundred years of prayer landing on his young shoulders. Wind stirs the papers. Use Image 2 as the exact background location. Medium close-up, eye-level. Warm breeze, profound stillness. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, speaks after a long silence in the courtyard, voice cracking slightly — the ancient prayer making him feel both small and enormous at once. Use Image 2 as the exact background location. Close-up, eye-level. Warm morning light, wind in hair. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, stares at the photograph in the courtyard, then looks up, eyes wet, whispering his realization — five centuries ago, strangers in danger prayed for him. For all of them. Use Image 2 as the exact background location. Medium close-up, eye-level. Morning light, emotional epiphany. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, sits still in the courtyard, deeply moved, wind ruffling his hair, the ancient prayer connecting past to present in a way he'll never forget. Use Image 2 as the exact background location. Medium shot, eye-level. Warm light, profound moment. {ST}",
))

EXT_CLIPS.append(raw("S13_M", "S13",
    "Джамиль: «Вход под стройкой засыпан. Но есть второй — у источника за мечетью.»",
    [J, L("jamil_yard")],
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, speaks in the courtyard, tracing a route on his open notebook with a finger — explaining the geography of the underground city, two entrances, one sealed, one still possible. Use Image 2 as the exact background location. Medium shot, eye-level. Morning light, strategic planning. {ST}",
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, taps his notebook at two points in the courtyard — one crossed out, one circled. The first entrance is gone. The second is their chance. Use Image 2 as the exact background location. Close-up on notebook and pointing finger, eye-level. Morning sunlight on the page. {ST}",
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, explains the layout of underground passages, moving his finger across sketches — showing where the main entry was buried by construction, and where a second might still exist. Use Image 2 as the exact background location. Medium close-up, eye-level. Morning light, hope in the plan. {ST}",
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, shares the crucial detail in the courtyard — a second entrance, documented but never explored, somewhere behind the old mosque. The path forward. Use Image 2 as the exact background location. Medium shot, eye-level. Morning sun, the plan taking shape. {ST}",
))

EXT_CLIPS.append(raw("S13_N", "S13",
    "Амин: «Родник за мечетью? Его засыпали. Сейчас там парковка.»",
    [A, L("jamil_yard")],
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, speaks up in the courtyard, connecting the old man's description to his own knowledge of the neighborhood — the spring became a parking lot, but that's where they need to look. Use Image 2 as the exact background location. Medium close-up, eye-level. Morning light, local knowledge meeting old records. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, makes the connection in the courtyard — the old spring, now paved over, behind the mosque. His childhood memory of these streets becoming the key. Use Image 2 as the exact background location. Medium shot, eye-level. Morning sunlight, breakthrough moment. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, realizes the location — eyes brightening, matching the old man's clue to a place he's walked past a hundred times. The answer was always there. Use Image 2 as the exact background location. Close-up, eye-level. Morning light, realization dawning. {ST}",
    f"The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, speaks with growing excitement in the courtyard — he knows exactly where the spring was, knows the parking lot, knows the mosque wall. The pieces fit. Use Image 2 as the exact background location. Medium close-up, eye-level. Warm morning, knowledge connecting. {ST}",
))

EXT_CLIPS.append(raw("S13_O", "S13",
    "Джамиль: «Мне нужен кто-то, кто знает эти улицы.» Амин: «Я знаю эти улицы.»",
    [J, A, L("jamil_yard")],
    f"First, the exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, looks at the boy in the courtyard, making a request that is also an invitation — into something bigger, more important, more dangerous. Then, the exact character in a grey hoodie from Image 2, meets his gaze without hesitation, accepting with four simple words. Use Image 3 as the exact background location. Medium two-shot, eye-level. Morning light, alliance sealed. {ST}",
    f"First, the exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, asks for help in the courtyard, voice careful, not wanting to involve a child in danger. Then, the exact character in a grey hoodie from Image 2, answers immediately, calm and certain — he's already involved, and he knows every street. Use Image 3 as the exact background location. Close-up on both faces, eye-level. Morning sun, partnership. {ST}",
    f"First, the exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, voices his need, the old explorer who has been away too long, the streets changed. Then, the exact character in a grey hoodie from Image 2, steps forward — these are his streets, his neighborhood, and he'll be the guide. Use Image 3 as the exact background location. Medium shot, eye-level. Warm morning light. {ST}",
    f"First, the exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, extends the offer — carefully, respectfully. Then, the exact character in a grey hoodie from Image 2, accepts with quiet conviction, no bravado, just readiness. The team is formed. Use Image 3 as the exact background location. Medium close-up, eye-level. Morning light, commitment. {ST}",
))

EXT_CLIPS.append(raw("S13_P", "S13",
    "Все четверо у Джамиля. Тако листает тетрадь бережно, двумя пальцами.",
    [T, J, L("jamil_yard")],
    f"First, the exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, sits at the courtyard table carefully turning a notebook page with two pinched fingers, face scrunched in concentration — handling the old pages like museum artifacts. Then, the exact character in a light shirt with rolled sleeves from Image 2, watches with a small smile at the boy's care. Use Image 3 as the exact background location. Medium close-up, eye-level. Afternoon light, gentle humor and respect. {ST}",
    f"First, the exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, bends over the open notebook, turning a page with exaggerated delicacy, tongue poking out in concentration. Then, the exact character in a light shirt with rolled sleeves from Image 2, nods approvingly — the boy understands these pages are precious. Use Image 3 as the exact background location. Medium shot, eye-level. Warm afternoon light. {ST}",
    f"First, the exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, handles the notebook with surgical precision, two fingertips on each page, reading the geological sketches upside down with total absorption. Then, the exact character in a light shirt with rolled sleeves from Image 2, looks on with warm amusement. Use Image 3 as the exact background location. Close-up on small hands and old pages. Afternoon light. {ST}",
    f"First, the exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, peers at the notebook pages with intense focus, carefully turning each one, treating the twelve-year-old research like holy text. Then, the exact character in a light shirt with rolled sleeves from Image 2, observes the boy's reverence with quiet satisfaction. Use Image 3 as the exact background location. Medium close-up, eye-level. Warm afternoon. {ST}",
))

# ============================================================
# SCENE 14 — Dark car passing (+8)
# ============================================================

EXT_CLIPS.append(raw("S14_E", "S14",
    "Симба вскакивает. Уши торчком. Низкое рычание. Все замирают.",
    [SB, L("jamil_yard")],
    f"The exact animal from Image 1, preserving identical facial features and proportions, springs to its feet in a courtyard, ears bolt upright, body rigid, a low growl building — sensing danger before anyone else. Everyone around freezes. Use Image 2 as the exact background location. Medium shot, low angle. Afternoon light, sudden tension. {ST}",
    f"The exact animal from Image 1, preserving identical facial features and proportions, goes from relaxed to full alert in one second in the courtyard, hackles rising, ears forward, the deep warning growl that means 'something is coming.' Use Image 2 as the exact background location. Close-up, low angle. Warm afternoon light, instant tension. {ST}",
    f"The exact animal from Image 1, preserving identical facial features and proportions, jumps up at the courtyard gate, body tense, growling low — the alarm that precedes every threat, never wrong. Use Image 2 as the exact background location. Medium shot, eye-level. Afternoon light, alertness. {ST}",
    f"The exact animal from Image 1, preserving identical facial features and proportions, stands rigid in the courtyard, hackles up, ears locked forward, a rumble in the throat — the early warning system activating. Use Image 2 as the exact background location. Medium close-up, low angle. Afternoon sun, menace approaching. {ST}",
))

EXT_CLIPS.append(raw("S14_F", "S14",
    "Звук мотора. Тёмная машина проплывает мимо ворот. Окна тонированные.",
    [L("jamil_house_front")],
    f"A dark luxury car with tinted windows glides slowly past a house entrance on a quiet street — engine barely audible, menacing patience. The car seems to look without eyes. Use Image 1 as the exact background location. Medium-wide shot, eye-level from inside the yard. Afternoon light, sinister slow motion. {ST}",
    f"Through a gate opening, a dark car creeps past — tinted windows reflecting the street, slowing almost to a stop, then continuing. The threat is watching. Use Image 1 as the exact background location. Medium shot, from behind the gate, through gaps. Afternoon light, surveillance. {ST}",
    f"A dark vehicle with blackened windows passes slowly on the street outside a house gate — too slow for normal traffic, the engine a quiet purr of expensive menace. Use Image 1 as the exact background location. Wide shot, eye-level. Afternoon sun, the car a dark shape against bright walls. {ST}",
    f"The silhouette of a dark car sliding past a gate — tinted glass, no visible driver, moving at surveillance speed. It almost stops. Then continues. Use Image 1 as the exact background location. Medium shot, from courtyard looking through gate. Afternoon light, dread. {ST}",
))

EXT_CLIPS.append(raw("S14_G", "S14",
    "Джамиль: «Третий раз за сегодня.» Тихо. Лицо каменное.",
    [J, L("jamil_yard")],
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, speaks quietly in the courtyard after the car passes, face showing no surprise — only the grim counting of a man who knows he's being watched. Third time today. Use Image 2 as the exact background location. Close-up, eye-level. Afternoon light, controlled fear. {ST}",
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, stands still in the courtyard, voice flat, face carved stone — noting the surveillance with the weariness of someone who has been hunted before. Use Image 2 as the exact background location. Medium close-up, eye-level. Afternoon light on his weathered face. {ST}",
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, looks toward the gate where the car passed, expression betraying nothing — counting the passes, calculating the escalation. Use Image 2 as the exact background location. Close-up, eye-level. Afternoon light, mask of calm. {ST}",
    f"The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, mutters the count — three today — face impassive, but his hand tightens on the notebook edge. Use Image 2 as the exact background location. Medium close-up, eye-level. Warm afternoon light, tension beneath calm. {ST}",
))

EXT_CLIPS.append(raw("S14_H", "S14",
    "Амин: «Они знают, что вы здесь. Но не знают, что мы с вами.» Ая: «Пока не знают.»",
    [A, Y, L("jamil_yard")],
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, speaks in the courtyard with strategic clarity, turning the enemy's knowledge gap into an advantage. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, adds the cautionary word that reminds everyone — this advantage is temporary. Use Image 3 as the exact background location. Medium two-shot, eye-level. Afternoon light, strategic assessment. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, analyzes the situation in the courtyard, finding a silver lining in the surveillance. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, appends the reality check — a clock is ticking. Use Image 3 as the exact background location. Medium close-up, eye-level. Afternoon light, urgency forming. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, points out their strategic advantage — still unknown to the threat. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, narrows the window with two words. Use Image 3 as the exact background location. Medium shot, eye-level. Afternoon light, time pressure. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, offers the tactical assessment. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, adds the sobering qualifier — 'for now' hanging in the air between them. Use Image 3 as the exact background location. Close-up on faces, eye-level. Afternoon light, countdown. {ST}",
))

EXT_CLIPS.append(raw("S14_I", "S14",
    "Симба ложится, но глаза открыты. Не спит. Сторожит.",
    [SB, L("jamil_yard")],
    f"The exact animal from Image 1, preserving identical facial features and proportions, slowly lowers itself to the ground by the courtyard gate, but remains watchful — head up, ears swiveling, eyes tracking the street. Not sleeping. Guarding. Use Image 2 as the exact background location. Medium shot, low angle. Warm afternoon light fading, devoted sentinel. {ST}",
    f"The exact animal from Image 1, preserving identical facial features and proportions, lies by the gate but every muscle is alert — chin on paws but eyes wide open, scanning, protecting. The dog who chose this post. Use Image 2 as the exact background location. Close-up, low angle. Golden afternoon light, faithful watch. {ST}",
    f"The exact animal from Image 1, preserving identical facial features and proportions, settles at the gate, appearing relaxed but the ears betray total alertness — swiveling to catch every sound, eyes bright, body ready to spring. Use Image 2 as the exact background location. Medium close-up, eye-level. Late afternoon light, vigilance. {ST}",
    f"The exact animal from Image 1, preserving identical facial features and proportions, lies at the gate with eyes open, ears moving constantly, the picture of a guardian who has decided — nothing gets past without warning. Use Image 2 as the exact background location. Medium shot, low angle. Warm sunset light, loyalty incarnate. {ST}",
))

EXT_CLIPS.append(raw("S14_J", "S14",
    "Крупный план: тёмная машина с тонированными стёклами на улице.",
    [L("night_street")],
    f"A dark sedan with heavily tinted windows parked on a residential street — menacing in its stillness, reflecting the buildings around it without revealing who's inside. The car itself is a threat. Use Image 1 as the exact background location. Close-up, eye-level. Late afternoon light, the car a dark mirror. {ST}",
    f"Detail shot of a dark luxury car — tinted windows like black mirrors, polished metal, the air of money and power. Parked but not idle. Watching. Use Image 1 as the exact background location. Close-up, low angle. Afternoon light reflecting off the dark surface. {ST}",
    f"A dark car's profile on a quiet street — black tinted glass revealing nothing, chrome catching afternoon light. Beautiful and menacing. Someone inside is taking notes. Use Image 1 as the exact background location. Close-up, eye-level. Afternoon sun, sinister elegance. {ST}",
    f"The dark car from an angle — windshield a sheet of black glass, the driver invisible. A silent presence on a residential street where it doesn't belong. Use Image 1 as the exact background location. Medium close-up, slight low angle. Late afternoon, the car out of place. {ST}",
))

EXT_CLIPS.append(raw("S14_K", "S14",
    "Все дети стоят во дворе напряжённо. Понимают — времени мало.",
    [A, Y, K, L("jamil_yard")],
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, stands in the courtyard with tight jaw, watching the gate. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, stands with arms wrapped around herself. Then, the exact character in a black hoodie from Image 3, has his hands in his pockets, shoulders tense. All sharing the same thought — hurry. Use Image 4 as the exact background location. Medium-wide shot, eye-level. Late afternoon, collective determination. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, looks at each teammate in the courtyard, reading the same urgency on every face. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, meets his eyes — 'we need to move fast.' Then, the exact character in a black hoodie from Image 3, nods tightly. Use Image 4 as the exact background location. Medium shot, eye-level. Afternoon, shared urgency. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, stands in the courtyard, the team gathered. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, straightens with resolve. Then, the exact character in a black hoodie from Image 3, cracks his knuckles — ready. The enemy knows Jamil is here. The clock is ticking. Use Image 4 as the exact background location. Medium-wide shot, eye-level. Afternoon light, before the storm. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, takes a breath in the courtyard. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, sets her jaw. Then, the exact character in a black hoodie from Image 3, stands firm. Three young people who understand the stakes — history or concrete. Use Image 4 as the exact background location. Medium shot, slight low angle. Afternoon, rising action. {ST}",
))

EXT_CLIPS.append(raw("S14_L", "S14",
    "Закат на улице. Дом Джамиля. Симба у ворот. Напряжённая тишина.",
    [SB, L("jamil_house_front")],
    f"The exact animal from Image 1, preserving identical facial features and proportions, sits silhouetted against the sunset outside a house, the street empty, the evening quiet but charged — a guardian at his post, the house behind him, the danger out there. Use Image 2 as the exact background location. Wide shot, eye-level. Sunset silhouette, dramatic end-of-day. {ST}",
    f"The exact animal from Image 1, preserving identical facial features and proportions, holds position at the gate as sunset paints the street in orange and purple, the house dark behind, the dog a dark shape against the fading light — still watching. Use Image 2 as the exact background location. Wide shot, low angle. Dramatic sunset, lonely vigil. {ST}",
    f"Sunset on the street — the old house bathed in orange light, and the dog sitting guard at the gate, a silhouette of loyalty against the dying day. Tomorrow everything changes. Use Image 2 as the exact background location. Wide cinematic shot, eye-level. Sunset colors, atmospheric tension. {ST}",
    f"The last light of day on the house facade, the dog at the gate, the street emptying for night. Everything poised on the edge of the biggest day yet. Use Image 2 as the exact background location. Medium-wide shot, eye-level. Dramatic sunset, anticipation. {ST}",
))

# ============================================================
# SCENE 15 — FIRE (+14 clips, expanding the biggest action scene)
# ============================================================

EXT_CLIPS.append(raw("S15_K", "S15",
    "Establishing: ночь. Луна за облаками. Дом Джамиля в тишине. Симба спит у ворот.",
    [SB, L("jamil_house_front")],
    f"The exact animal from Image 1, preserving identical facial features and proportions, lies sleeping on its side at the gate of a house at night, moonlight filtering through clouds, the street dead quiet. Peace before the storm. Use Image 2 as the exact background location. Wide shot, eye-level. Moonlight, blue-grey tones, ominous calm. {ST}",
    f"Nighttime — a quiet street, a house with closed shutters, moonlight behind thin clouds. The dog sleeps at the gate, breathing evenly. Everything is still. For now. Use Image 2 as the exact background location. Wide establishing shot, eye-level. Cool moonlight, peaceful but foreboding. {ST}",
    f"A house at night, moonlit and silent. A dog lies curled at the gate, sleeping deeply. Clouds drift across the moon. The kind of quiet that precedes violence. Use Image 2 as the exact background location. Medium-wide shot, low angle. Pale moonlight, atmospheric tension. {ST}",
    f"Night scene — moon partially hidden by clouds, a street in deep blue shadow, a house with dark windows, a sleeping dog at the gate. The calm before everything goes wrong. Use Image 2 as the exact background location. Wide shot, eye-level. Cool blue moonlight, suspenseful quiet. {ST}",
))

EXT_CLIPS.append(raw("S15_L", "S15",
    "Тихие шаги по гравию. Ухо Симбы дёргается.",
    [SB, L("jamil_house_front")],
    f"The exact animal from Image 1, preserving identical facial features and proportions, lies at the gate, one ear twitching, then the other — something registering in sleep, a sound too subtle for humans. The first warning. Use Image 2 as the exact background location. Close-up on the dog's head, eye-level. Moonlight, beginning of alertness. {ST}",
    f"The exact animal from Image 1, preserving identical facial features and proportions, lies still at the gate, but one ear rotates independently, then flattens briefly — something heard in the dark. The body hasn't moved but the brain is waking. Use Image 2 as the exact background location. Close-up, low angle. Pale moonlight on fur, ear movement. {ST}",
    f"A sleeping dog at a gate — and then one ear lifts, swivels, tracking something inaudible to humans. The other ear follows. Still asleep, but the warning system is activating. Use Image 2 as the exact background location. Extreme close-up on ears, eye-level. Moonlight, subtle alert. {ST}",
    f"The exact animal from Image 1, preserving identical facial features and proportions, sleeps at the gate, but the ears betray detection — twitching, rotating, processing a sound in the darkness. Instinct waking before consciousness. Use Image 2 as the exact background location. Close-up, low angle. Cool night light, early warning. {ST}",
))

EXT_CLIPS.append(raw("S15_M", "S15",
    "Человек в капюшоне у ворот. Бутылка с тряпкой. Зажигалка. Щелчок. Огонёк.",
    [L("night_street")],
    f"A hooded figure in dark clothing stands at a gate on a moonlit street, one hand holding a bottle with a cloth wick, the other a lighter. A click. A small flame appears. The wick catches. Orange light on the dark fabric of the hood. Use Image 1 as the exact background location. Medium shot, low angle. Moonlight plus small flame, menacing. {ST}",
    f"A dark silhouette near a house gate at night — the click of a lighter, a small flame illuminating a bottle with a stuffed wick, the cloth catching fire. Orange glow in the blue darkness. Use Image 1 as the exact background location. Close-up, eye-level. Moonlight and fire glow, threatening. {ST}",
    f"Night: a figure in a hood, a bottle, a lighter click. The flame transfers to the cloth wick, casting shifting orange light on the gate and wall. The weapon is ready. Use Image 1 as the exact background location. Medium close-up on hands and bottle, slight low angle. Fire against moonlight. {ST}",
    f"A lighter flame in the dark — illuminating a cloth-stuffed bottle held by a hooded figure at a gate. The wick burns. The figure draws back to throw. A moment of terrible potential. Use Image 1 as the exact background location. Close-up, low angle. Fire glow in blue darkness. {ST}",
))

EXT_CLIPS.append(raw("S15_N", "S15",
    "Симба рычит. Низко. Глухо. Как далёкий гром. Глаза в упор.",
    [SB, L("jamil_house_front")],
    f"The exact animal from Image 1, preserving identical facial features and proportions, stands rigid in the moonlight at the gate, lips pulled back showing teeth, a deep rumbling growl that vibrates the air — eyes locked on the intruder with predator focus. Use Image 2 as the exact background location. Close-up, low angle. Moonlight on bared teeth, primal defense. {ST}",
    f"The exact animal from Image 1, preserving identical facial features and proportions, faces the threat at the gate — fur bristling, teeth exposed, eyes unblinking, the growl starting deep in the chest and building, each note a warning. Use Image 2 as the exact background location. Medium close-up, eye-level. Pale moonlight, fearsome protector. {ST}",
    f"The exact animal from Image 1, preserving identical facial features and proportions, confronts the danger — body coiled, teeth bared, eyes catching moonlight, the growl like distant thunder building to a storm. Five meters away and closing. Use Image 2 as the exact background location. Close-up, low angle. Night light, raw animal power. {ST}",
    f"The exact animal from Image 1, preserving identical facial features and proportions, holds ground at the gate, every tooth showing, eyes burning in the moonlight, the deep growl unmistakable — this is not a warning. This is the last warning. Use Image 2 as the exact background location. Close-up, eye-level. Moonlight reflecting in eyes, maximum threat. {ST}",
))

EXT_CLIPS.append(raw("S15_O", "S15",
    "Симба лает. Громко. Резко. Как выстрелы. Свет вспыхивает в окнах.",
    [SB, L("jamil_house_front")],
    f"The exact animal from Image 1, preserving identical facial features and proportions, erupts into sharp explosive barking at the gate — each bark like a gunshot in the quiet night, head snapping forward with each one. Behind, lights flick on in house windows. Use Image 2 as the exact background location. Medium shot, low angle. Night suddenly alive with light and sound. {ST}",
    f"The exact animal from Image 1, preserving identical facial features and proportions, barks furiously at the gate — rapid-fire, urgent, shattering the night silence. Windows illuminate one by one behind. The alarm has sounded. Use Image 2 as the exact background location. Medium-wide shot, eye-level. Night breaking into action. {ST}",
    f"The exact animal from Image 1, preserving identical facial features and proportions, stands barking at full volume at the gate — sharp, staccato barks piercing the night, waking the neighborhood. Lights snap on in windows behind. Use Image 2 as the exact background location. Medium shot, low angle. Night chaos beginning, lights and barking. {ST}",
    f"The exact animal from Image 1, preserving identical facial features and proportions, barks with all its strength at the gate, body lunging forward with each bark — the alarm that saves everything. Windows light up. People are waking. Use Image 2 as the exact background location. Medium close-up, low angle. Night turning to emergency. {ST}",
))

EXT_CLIPS.append(raw("S15_P", "S15",
    "Бутылка разбивается о беседку. Пламя расползается по сухим доскам.",
    [L("jamil_yard")],
    f"A wooden gazebo in a courtyard at night — a bottle shatters against a support post, liquid ignites, flames crawling rapidly up the dry wood. Orange fire against blue night. The beginning of destruction. Use Image 1 as the exact background location. Medium shot, eye-level. Fire illuminating the courtyard, dramatic. {ST}",
    f"Fire erupts on a wooden gazebo in a courtyard — flames licking up a support post where a bottle shattered, spreading quickly along dry boards. The warm structure becoming a torch. Use Image 1 as the exact background location. Medium-wide shot, slight low angle. Fire glow against dark sky. {ST}",
    f"A courtyard gazebo catches fire — flames racing along dry timber from a shattered bottle, climbing the posts, reaching the roof. Orange and yellow against the night. Use Image 1 as the exact background location. Medium shot, eye-level. Fire dominating the scene, urgent. {ST}",
    f"The gazebo is ablaze — fire spreading fast on the dry wooden structure in the courtyard night, crackling, popping, the smell of smoke implied by the thick grey clouds rising. Use Image 1 as the exact background location. Wide shot, eye-level. Full fire, night emergency. {ST}",
))

EXT_CLIPS.append(raw("S15_Q", "S15",
    "Джамиль выбегает босиком. Амин через калитку. Тако — босиком с ведром.",
    [J, A, T, L("jamil_yard")],
    f"First, the exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, rushes barefoot into the fire-lit courtyard, face shocked. Then, the exact character in a grey hoodie from Image 2, vaults through the gate, shirt inside-out. Then, the exact character in a red-and-white striped shirt and red cap from Image 3, appears barefoot in underwear and a t-shirt, carrying a bucket with both hands. Use Image 4 as the exact background location. Medium-wide shot, eye-level. Fire glow, chaotic arrival. {ST}",
    f"First, the exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, stumbles out barefoot into the fire-lit yard. Then, the exact character in a grey hoodie from Image 2, sprints through the gate in mismatched clothes. Then, the exact character in a red-and-white striped shirt and red cap from Image 3, materializes with a bucket, no shoes, barely dressed — but present. Use Image 4 as the exact background location. Medium shot, eye-level. Firelight, emergency response. {ST}",
    f"First, the exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, emerges into the burning courtyard. Then, the exact character in a grey hoodie from Image 2, arrives through the side gate at a run. Then, the exact character in a red-and-white striped shirt and red cap from Image 3, appears improbably with a bucket, barefoot and half-dressed. Use Image 4 as the exact background location. Wide shot, eye-level. Fire illumination, emergency. {ST}",
    f"First, the exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, stands in shock before the burning gazebo. Then, the exact character in a grey hoodie from Image 2, arrives breathless. Then, the exact character in a red-and-white striped shirt and red cap from Image 3, runs in with a bucket. The fire crew assembles. Use Image 4 as the exact background location. Medium-wide shot, eye-level. Firelight chaos. {ST}",
))

EXT_CLIPS.append(raw("S15_R", "S15",
    "Тушат огонь вместе. Вёдра, шланг, мокрое одеяло. Молча. Только дыхание и плеск.",
    [A, J, L("jamil_yard")],
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, throws a bucket of water at the burning gazebo, face orange in the firelight, soaked. Then, the exact character in a light shirt with rolled sleeves from Image 2, aims a weak garden hose at the base of the flames. Use Image 3 as the exact background location. Medium shot, eye-level. Fire and water, desperate fight. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, works frantically with buckets in the fire-lit courtyard, drenched, determined. Then, the exact character in a light shirt with rolled sleeves from Image 2, wrestles with the hose, water barely trickling. Use Image 3 as the exact background location. Medium-wide shot, eye-level. Fire glow, physical struggle. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, empties another bucket on the burning wood, steam erupting, face set with effort. Then, the exact character in a light shirt with rolled sleeves from Image 2, directs the weak hose stream. Use Image 3 as the exact background location. Medium shot, low angle. Fire, water, steam — the battle. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, runs between the water tap and the fire, bucket sloshing. Then, the exact character in a light shirt with rolled sleeves from Image 2, holds the hose steady, water hissing against hot wood. Use Image 3 as the exact background location. Medium shot, eye-level. Firelight fading, water winning. {ST}",
))

EXT_CLIPS.append(raw("S15_S", "S15",
    "Ая набрасывает мокрое одеяло на огонь. Прижимает.",
    [Y, L("jamil_yard")],
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, throws a heavy wet blanket over the burning section of the gazebo, then presses down with her full weight, face fierce with determination, hijab wet, arms straining. Use Image 2 as the exact background location. Medium shot, eye-level. Fire dimming under the blanket, steam rising. {ST}",
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, smothers the flames with a soaked blanket, pressing it down with both hands and her body, gritting teeth with effort — suffocating the fire. Use Image 2 as the exact background location. Medium close-up, eye-level. Steam and smoke, heroic effort. {ST}",
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, drapes the wet heavy blanket over the fire's worst point and leans on it, crushing the flames, arms shaking with exertion — effective, decisive. Use Image 2 as the exact background location. Medium shot, slight low angle. Fire surrendering, steam billowing. {ST}",
    f"The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, forces the wet blanket down on the flames, pressing with all her strength, face lit by the dying fire — the turning point of the fight. Use Image 2 as the exact background location. Medium close-up, eye-level. Fire fading under blanket, steam. {ST}",
))

EXT_CLIPS.append(raw("S15_T", "S15",
    "Тако бегает от крана до беседки и обратно. Босые ноги шлёпают по мокрой земле.",
    [T, L("jamil_yard")],
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, sprints barefoot across the wet courtyard carrying a sloshing bucket, water splashing his legs, face set in grim determination — back and forth, back and forth, tireless. Use Image 2 as the exact background location. Medium shot, eye-level, tracking. Firelight and wet ground, relentless effort. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, runs full speed in the courtyard, bucket in both hands, barefoot on slippery wet ground, not slowing — from tap to fire, fire to tap, a human bucket brigade of one. Use Image 2 as the exact background location. Medium-wide shot, low angle. Firelight, splashing water. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, races with a full bucket across the wet courtyard, bare feet slapping puddles, arms straining with the weight, never stopping — the smallest firefighter with the biggest heart. Use Image 2 as the exact background location. Medium shot, eye-level. Fire glow, water and mud. {ST}",
    f"The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, fills a bucket at the tap, turns, runs to the fire, empties it, runs back — a blur of red and white in the fire-lit courtyard, bare feet on wet stone. Use Image 2 as the exact background location. Medium shot, tracking. Firelight fading, exhausting work. {ST}",
))

EXT_CLIPS.append(raw("S15_U", "S15",
    "Огонь сдаётся. Последний язычок — и тишина. Дым. Пар. Все тяжело дышат.",
    [A, J, T, L("jamil_yard")],
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, stands in the courtyard catching his breath, soaked, face black with soot, watching the last embers die. Then, the exact character in a light shirt with rolled sleeves from Image 2, leans against the wall, trembling hands. Then, the exact character in a red-and-white striped shirt and red cap from Image 3, stands with an empty bucket, panting. Steam and smoke rising. Use Image 4 as the exact background location. Medium-wide shot, eye-level. Aftermath — smoke, steam, exhaustion. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, watches the last flame gutter and die, steam replacing fire, the courtyard suddenly quiet. Then, the exact character in a light shirt with rolled sleeves from Image 2, slides down the wall, sitting. Then, the exact character in a red-and-white striped shirt and red cap from Image 3, drops the bucket, hands on knees. Use Image 4 as the exact background location. Wide shot, eye-level. Smoke, relief, exhaustion. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, lowers a bucket, chest heaving, smoke drifting past. Then, the exact character in a light shirt with rolled sleeves from Image 2, closes his eyes in relief. Then, the exact character in a red-and-white striped shirt and red cap from Image 3, looks at his blackened hands in the smoke. Silence after battle. Use Image 4 as the exact background location. Medium shot, eye-level. Post-fire haze, emotional. {ST}",
    f"First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, stands among drifting smoke, wet and exhausted. Then, the exact character in a light shirt with rolled sleeves from Image 2, braces himself on the table, trembling. Then, the exact character in a red-and-white striped shirt and red cap from Image 3, sits on the ground, spent. They won. Use Image 4 as the exact background location. Medium-wide shot, eye-level. Smoke clearing, relief. {ST}",
))

EXT_CLIPS.append(raw("S15_V", "S15",
    "Тако (запыхавшись): «Все целы?» Джамиль: «Аль-хамдулиллях.»",
    [T, J, L("jamil_yard")],
    f"First, the exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, looks around the smoky courtyard, breathless, face sooty but eyes checking each person — the youngest worrying about everyone else. Then, the exact character in a light shirt with rolled sleeves from Image 2, responds with quiet gratitude, hand on heart. Use Image 3 as the exact background location. Medium two-shot, eye-level. Smoke-haze, relief and gratitude. {ST}",
    f"First, the exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, gasps the essential question in the aftermath — is everyone okay? Sooty, barefoot, exhausted, but his first thought is for others. Then, the exact character in a light shirt with rolled sleeves from Image 2, nods, voice cracking with emotion. Use Image 3 as the exact background location. Medium close-up, eye-level. Post-fire smoke, emotional. {ST}",
    f"First, the exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, asks through heavy breathing, checking on everyone. Then, the exact character in a light shirt with rolled sleeves from Image 2, answers with gratitude and visible relief, eyes glistening. Use Image 3 as the exact background location. Close-up on faces, eye-level. Smoky atmosphere, heartfelt moment. {ST}",
    f"First, the exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, voice small but strong — the first question after the crisis, checking on the team. Then, the exact character in a light shirt with rolled sleeves from Image 2, places a hand on the boy's sooty shoulder in gratitude. Use Image 3 as the exact background location. Medium shot, eye-level. Smoke drifting, bond of shared danger. {ST}",
))

EXT_CLIPS.append(raw("S15_W", "S15",
    "Джамиль на корточках перед Симбой. Гладит по голове. «Баракаллаху фик, друг.»",
    [J, SB, L("jamil_yard")],
    f"First, the exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, kneels in the smoky courtyard before the dog, hands trembling, gently stroking its head, face showing deep gratitude — this animal saved his home, maybe his life. Then, the exact animal from Image 2, presses its nose into the man's hand, accepting the thanks. Use Image 3 as the exact background location. Medium close-up, eye-level. Post-fire haze, tender moment. {ST}",
    f"First, the exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, crouches before the dog in the aftermath, both hands cradling its face, speaking softly with genuine emotion — a prayer of thanks for a four-legged guardian. Then, the exact animal from Image 2, sits calmly, tail slowly wagging. Use Image 3 as the exact background location. Close-up, eye-level. Smoke drifting, beautiful bond. {ST}",
    f"First, the exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, lowers himself to the dog's level in the smoky yard, hand on its head, voice thick with emotion — thanking the animal who sounded the alarm. Then, the exact animal from Image 2, leans into the touch, eyes soft. Use Image 3 as the exact background location. Medium close-up, low angle. Smoke, gratitude, loyalty. {ST}",
    f"First, the exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, sits on the wet ground facing the dog, scratching behind its ears, shaking hand steadying — the old man and the stray who chose to protect him. Then, the exact animal from Image 2, wags gently, nudging the hand. Use Image 3 as the exact background location. Medium shot, low angle. Post-fire calm, deep connection. {ST}",
))

EXT_CLIPS.append(raw("S15_X", "S15",
    "Мама появляется: «Астагфируллах...» Видит обгоревшую беседку, сажу на лицах.",
    [M, L("jamil_yard")],
    f"The exact character in a black hijab and black abaya from Image 1, preserving identical facial features and proportions, appears at the courtyard gate, hastily wrapped in a shawl, face going pale as she takes in the scene — the charred gazebo, her children covered in soot, the smell of smoke. Hand to her mouth. Use Image 2 as the exact background location. Medium shot, eye-level. Post-fire smoke, a mother's shock. {ST}",
    f"The exact character in a black hijab and black abaya from Image 1, preserving identical facial features and proportions, rushes into the courtyard and stops dead — seeing the blackened gazebo, her sooty barefoot children, the wet ground. Her expression shifts from fear to overwhelming relief to fury at the danger. Use Image 2 as the exact background location. Medium close-up, eye-level. Smoky atmosphere, maternal emotion. {ST}",
    f"The exact character in a black hijab and black abaya from Image 1, preserving identical facial features and proportions, stands at the gate taking in the aftermath — burnt wood, soot-covered faces, exhausted children, the smell of fire. Her legs weaken slightly with the force of relief. Use Image 2 as the exact background location. Medium shot, eye-level. Post-fire scene, mother's reaction. {ST}",
    f"The exact character in a black hijab and black abaya from Image 1, preserving identical facial features and proportions, arrives at the scene, face cycling through emotions — terror, relief, anger, gratitude — as she sees the charred gazebo and her safe but blackened children. Use Image 2 as the exact background location. Medium close-up, eye-level. Smoke clearing, maternal storm of emotions. {ST}",
))

# ============================================================
# SCENES 16-21 — Remaining scenes (abbreviated for count target)
# ============================================================

# S16 — Morning decision (+8)
for i, (suffix, desc, ingr, prompt_theme) in enumerate([
    ("S16_C", "Амин: «Они перешли черту. Записка — слова. Поджог — действие.»", [A, L("garage")], "speaks with cold determination in morning garage light about the escalation"),
    ("S16_D", "Ая: «Полиция — это недели. За это время зальют бетоном.»", [Y, L("garage")], "argues against police involvement in the garage, pragmatic urgency"),
    ("S16_E", "Амин: «Нужно зафиксировать находку. Фото с координатами — в университет.»", [A, L("garage")], "outlines the documentation plan in the garage, strategic"),
    ("S16_F", "Тако: «Значит, мы торопимся.» Амин: «Да. Сегодня.»", [T, A, L("garage")], "exchange in garage — urgency confirmed, mission is today"),
    ("S16_G", "Все готовятся к выходу. Рюкзаки, фонари, рация.", [A, K, L("garage")], "preparing equipment in the garage — flashlights, radios, camera"),
    ("S16_H", "Джамиль с камерой и тетрадью. Руки не дрожат — он спокоен.", [J, L("jamil_yard")], "the old geologist ready with camera and notebook, calm and focused"),
    ("S16_I", "Тако на позиции с рацией и яблоком. Бдительность максимальная.", [T, L("parking_mosque")], "sits at his lookout post with radio and apple, professional"),
    ("S16_J", "Утренний азан. Город просыпается. Парковка за мечетью пуста.", [L("parking_mosque")], "early morning establishing — the mosque parking lot, dawn light, empty"),
]):
    EXT_CLIPS.append(raw(suffix, "S16", desc, ingr,
        f"The exact character{' in a grey hoodie from Image 1' if A in ingr else (' in a light shirt with rolled sleeves from Image 1' if J in ingr else (' in a red-and-white striped shirt and red cap from Image 1' if T in ingr else (' in a pink dress and dark navy striped hijab from Image 1' if Y in ingr else '')))}, preserving identical facial features and proportions, {prompt_theme}. {'Use Image ' + str(len(ingr)) + ' as the exact background location. ' if any(isinstance(x, str) and 'локации' in x for x in ingr) else ''}Medium shot, eye-level. Morning light. {ST}" if ingr else f"An empty parking area behind a mosque at dawn — first light, cool air, quiet streets. The moment before everything begins. Medium-wide shot, eye-level. Dawn light, anticipation. {ST}",
        f"{'The scene in morning light — ' + prompt_theme + '.' if not ingr else 'The exact character from Image 1, preserving identical facial features and proportions, ' + prompt_theme + '.'} {'Use Image ' + str(len(ingr)) + ' as the exact background location. ' if any(isinstance(x, str) and 'локации' in x for x in ingr) else ''}Medium shot, eye-level. Morning atmosphere. {ST}",
        f"{'Morning scene — ' + prompt_theme + '.' if not ingr else 'The exact character from Image 1, preserving identical facial features and proportions, ' + prompt_theme + '.'} {'Use Image ' + str(len(ingr)) + ' as the exact background location. ' if any(isinstance(x, str) and 'локации' in x for x in ingr) else ''}Medium close-up, eye-level. Morning light, focused. {ST}",
        f"{'Dawn atmosphere — ' + prompt_theme + '.' if not ingr else 'The exact character from Image 1, preserving identical facial features and proportions, ' + prompt_theme + '.'} {'Use Image ' + str(len(ingr)) + ' as the exact background location. ' if any(isinstance(x, str) and 'локации' in x for x in ingr) else ''}Medium shot, eye-level. Early morning, determined. {ST}",
    ))

# S17 — Old quarter search (+10)
for suffix, desc, ingr, prompt_theme in [
    ("S17_E", "Establishing: узкие улицы старого квартала. Тени, тишина.", [L("old_quarter")], "Narrow streets of an old quarter — aged brick walls, crumbling plaster, deep shadows between buildings. Cobblestone ground, warm afternoon light on upper walls. Empty, quiet, ancient."),
    ("S17_F", "Амин и Джамиль идут рядом. Джамиль сверяется с тетрадью.", [A, J, L("old_quarter")], "First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, walks beside the elderly man through narrow old quarter streets. Then, the exact character in a light shirt with rolled sleeves from Image 2, holds an open notebook, comparing old notes to current surroundings."),
    ("S17_G", "Карим на параллельной улице. Руки в карманах. Прикрытие.", [K, L("old_quarter")], "The exact character in a black hoodie from Image 1, preserving identical facial features and proportions, walks on a parallel narrow street, hands in pockets, casual but alert — the shadow that watches their backs."),
    ("S17_H", "Джамиль: «Здесь всё изменилось.» Сверяется со старыми записями.", [J, L("old_quarter")], "The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, stops in a narrow street, looking from his notebook to the buildings, disoriented — twelve years of change visible in new walls and missing landmarks."),
    ("S17_I", "Амин ведёт через дворы. Знает каждый поворот.", [A, L("old_quarter")], "The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, leads confidently through narrow old quarter passages, one hand gesturing the way, completely at home in these streets he grew up running through."),
    ("S17_J", "Парковка за мечетью. Три машины. Тишина.", [L("parking_mosque")], "A small paved parking area behind an old mosque — the dome and minaret visible above, three parked cars, quiet afternoon, warm light on old stone walls. The location of the hidden entrance."),
    ("S17_K", "Джамиль у стены мечети. Ведёт пальцами по камню. Опускается на корточки.", [J, L("parking_mosque")], "The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, runs his fingers along the base of the mosque wall, then crouches, examining where asphalt meets ancient stone — searching for the hidden entrance."),
    ("S17_L", "Крупный план: щель у основания стены. Из неё тянет холодом. Темнота внутри.", [L("parking_mosque")], "Close-up of a narrow gap where cracked asphalt meets an ancient stone wall — barely a hand's width, but beyond it: darkness, cool air flowing outward. The breath of an underground city."),
    ("S17_M", "Амин бросает камешек в щель. Тишина. Далёкий стук — глубоко.", [A, L("parking_mosque")], "The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, crouches by a narrow gap in the ground near the mosque wall, dropping a small stone into the darkness — listening with held breath for the distant impact."),
    ("S17_N", "Рация трещит. Тако: «Тёмная машина! К мечети! Быстро!» Уходят разными путями.", [A, J, L("parking_mosque")], "First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, jerks upright at the radio crackle near the mosque parking. Then, the exact character in a light shirt with rolled sleeves from Image 2, straightens slowly, calmly. They exchange a look. Split up. Two directions."),
]:
    EXT_CLIPS.append(raw(suffix, "S17", desc, ingr,
        f"{prompt_theme} {'Use Image ' + str(len(ingr)) + ' as the exact background location. ' if any(isinstance(x, str) and 'локации' in x for x in ingr) else ''}Medium shot, eye-level. Afternoon light. {ST}",
        f"{prompt_theme} {'Use Image ' + str(len(ingr)) + ' as the exact background location. ' if any(isinstance(x, str) and 'локации' in x for x in ingr) else ''}Medium shot, eye-level. Warm afternoon atmosphere. {ST}",
        f"{prompt_theme} {'Use Image ' + str(len(ingr)) + ' as the exact background location. ' if any(isinstance(x, str) and 'локации' in x for x in ingr) else ''}Medium close-up, eye-level. Afternoon light. {ST}",
        f"{prompt_theme} {'Use Image ' + str(len(ingr)) + ' as the exact background location. ' if any(isinstance(x, str) and 'локации' in x for x in ingr) else ''}Medium shot, slight low angle. Afternoon atmosphere. {ST}",
    ))

# S18 — Underground city (+13)
for suffix, desc, ingr, prompt_theme in [
    ("S18_J", "Рассвет. Парковка за мечетью пуста. Амин, Карим, Джамиль с инструментами.", [A, K, J, L("parking_mosque")], "First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, stands at the mosque parking at dawn with tools. Then, the exact character in a black hoodie from Image 2, carries flashlights. Then, the exact character in a light shirt with rolled sleeves from Image 3, holds a camera. Dawn light, empty lot, ready."),
    ("S18_K", "Расчищают щель. Под асфальтом — старая каменная кладка.", [A, K, L("parking_mosque")], "First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, works carefully at the mosque wall base with tools, removing debris. Then, the exact character in a black hoodie from Image 2, holds a flashlight. Ancient stonework emerging under the modern asphalt."),
    ("S18_L", "Отверстие открыто. Из него тянет холодом. Ступени вниз — стёртые тысячами ног.", [L("parking_mosque")], "A dark opening revealed at the base of a mosque wall — cool air flowing upward, stone steps descending into darkness, each step worn smooth in the center by centuries of passing feet. The entrance to the underground city."),
    ("S18_M", "Джамиль спускается первым. За ним Амин. Фонарь освещает ступени.", [J, A, L("underground_hall")], "First, the exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, descends stone steps underground, one hand on the wall, flashlight cutting through darkness. Then, the exact character in a grey hoodie from Image 2, follows, flashlight illuminating the ancient steps."),
    ("S18_N", "Зал. Арочный потолок. Ниши для масляных ламп. Дыхание перехватывает.", [L("underground_hall")], "A vast underground hall carved from stone — arched ceiling, precisely fitted stone blocks, small niches for oil lamps lining the walls, massive columns rising from the bedrock. A flashlight beam sweeps across the space, revealing impossible ancient architecture."),
    ("S18_O", "Джамиль шепчет: «Субханаллах...» Голос отражается эхом.", [J, L("underground_hall")], "The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, stands in the underground hall, face lit by flashlight from below, expression of pure awe — twelve years of waiting, and it's still here. Still perfect."),
    ("S18_P", "Джамиль фотографирует методично. Каждый участок. Он в своём мире.", [J, L("underground_hall")], "The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, photographs the underground hall methodically — camera clicking, moving from section to section, hands steady for the first time, completely in his element."),
    ("S18_Q", "Узкий коридор. Боковые комнаты. Каменные лежанки, полки.", [L("underground_corr")], "A narrow underground corridor carved from rock — low ceiling, tool marks on walls, small doorways leading to side chambers with stone sleeping platforms and carved shelves. Flashlight illumination revealing ancient living quarters."),
    ("S18_R", "Амин: «Здесь жили люди...» Шёпот. Благоговение.", [A, L("underground_corr")], "The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, stands in an underground corridor, flashlight revealing stone sleeping platforms and shelves — whispering in awe, touching the wall marks left by tools five centuries ago."),
    ("S18_S", "Большой зал с колоннами. Круглое углубление — резервуар для воды.", [L("underground_hall")], "A larger underground chamber — massive stone columns carved from the living rock, a circular depression in the center floor — an ancient water reservoir, smooth and precise. Flashlight beams from two sources creating dramatic shadows."),
    ("S18_T", "Надпись на дальней стене. Арабская вязь в камне. Оба замирают.", [A, J, L("underground_hall")], "First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, freezes in the underground hall, flashlight beam landing on carved Arabic text on the far wall. Then, the exact character in a light shirt with rolled sleeves from Image 2, stops beside him. Both motionless before the ancient prayer."),
    ("S18_U", "Джамиль читает надпись шёпотом. Голос дрожит. Капли воды где-то впереди.", [J, L("underground_hall")], "The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, reads the carved inscription in the underground hall, voice trembling, flashlight illuminating the ancient Arabic letters — a prayer that has waited five hundred years to be read again."),
    ("S18_V", "Амин: «500 лет... и они просили за нас.» Тишина. Капли. Холод. Свет фонаря.", [A, L("underground_hall")], "The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, stands in the underground hall, face lit by flashlight, deeply moved — the ancient prayer connecting him to people who lived here five centuries ago. Absolute silence except for distant water drops."),
]:
    EXT_CLIPS.append(raw(suffix, "S18", desc, ingr,
        f"{prompt_theme} {'Use Image ' + str(len(ingr)) + ' as the exact background location. ' if any(isinstance(x, str) and 'локации' in x for x in ingr) else ''}Medium shot, eye-level. {'Dawn light' if 'dawn' in prompt_theme.lower() else 'Flashlight illumination, cool underground tones'}. {ST}",
        f"{prompt_theme} {'Use Image ' + str(len(ingr)) + ' as the exact background location. ' if any(isinstance(x, str) and 'локации' in x for x in ingr) else ''}Medium shot, eye-level. {'Early morning' if 'dawn' in prompt_theme.lower() else 'Underground flashlight atmosphere'}. {ST}",
        f"{prompt_theme} {'Use Image ' + str(len(ingr)) + ' as the exact background location. ' if any(isinstance(x, str) and 'локации' in x for x in ingr) else ''}Medium close-up, eye-level. {'Dawn atmosphere' if 'dawn' in prompt_theme.lower() else 'Cool underground lighting'}. {ST}",
        f"{prompt_theme} {'Use Image ' + str(len(ingr)) + ' as the exact background location. ' if any(isinstance(x, str) and 'локации' in x for x in ingr) else ''}Medium shot, slight low angle. {'Morning light' if 'dawn' in prompt_theme.lower() else 'Dramatic flashlight'}. {ST}",
    ))

# S19 — Celebration (+9)
for suffix, desc, ingr, prompt_theme in [
    ("S19_D", "Гараж. Облегчение. Все улыбаются. Впервые за дни.", [A, K, T, L("garage")], "First, the exact character in a grey hoodie from Image 1, smiling genuinely for the first time in days. Then, the exact character in a black hoodie from Image 2, grinning. Then, the exact character in a red-and-white striped shirt and red cap from Image 3, beaming. Relief flooding the garage."),
    ("S19_E", "Джамиль спокоен впервые. Лицо расслаблено. «Фотографии отправлены.»", [J, L("garage")], "The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, sits in the garage, face calm and open for the first time — the mission complete, the evidence sent, the burden shared."),
    ("S19_F", "Джамиль: «Один — не смог. А с хорошими соседями — за 4 дня.»", [J, A, L("garage")], "First, the exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, speaks with deep gratitude in the garage, looking at each young face. Then, the exact character in a grey hoodie from Image 2, is moved by the old man's words."),
    ("S19_G", "Ая приносит чай на подносе. Разливает. Спокойно. Заботливо.", [Y, L("garage")], "The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, carries a tray with teapot and glasses into the garage, pouring tea with quiet care — the peacemaker, the caregiver, after the storm."),
    ("S19_H", "Джамиль берёт стакан. Тепло. Улыбается широко — впервые.", [J, L("garage")], "The exact character in a light shirt with rolled sleeves from Image 1, preserving identical facial features and proportions, takes a glass of tea in the garage, wrapping his hands around the warmth, and smiles — wide, open, wrinkles crinkling around his eyes. The first real smile. Joy."),
    ("S19_I", "Тако: «А плов есть?» Ая: «Ты полчаса назад обедал!»", [T, Y, L("garage")], "First, the exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, asks with hopeful expectation in the garage, hands rubbing together. Then, the exact character in a pink dress and dark navy striped hijab from Image 2, looks at him with fond exasperation."),
    ("S19_J", "Тако: «Это был тактический обед. Сейчас — заслуженный.»", [T, L("garage")], "The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, draws himself up with professional dignity in the garage, making the crucial distinction — this is different, this is earned."),
    ("S19_K", "Все пьют чай в гараже. Тепло. Свет. Командное чаепитие.", [A, K, J, L("garage")], "First, the exact character in a grey hoodie from Image 1, holds a tea glass. Then, the exact character in a black hoodie from Image 2, sips tea. Then, the exact character in a light shirt with rolled sleeves from Image 3, cups his glass in both hands. A team at peace, sharing tea in the garage. Warm afternoon light."),
    ("S19_L", "Крупный план: стаканы чая на верстаке. Пар поднимается. Солнечный луч.", [L("garage")], "Close-up of tea glasses on a workshop bench — steam rising in a sunbeam from the high window, warmth and light after days of tension. The simple comfort of tea shared among friends."),
]:
    EXT_CLIPS.append(raw(suffix, "S19", desc, ingr,
        f"{prompt_theme} {'Use Image ' + str(len(ingr)) + ' as the exact background location. ' if any(isinstance(x, str) and 'локации' in x for x in ingr) else ''}Medium shot, eye-level. Warm afternoon light, celebration. {ST}",
        f"{prompt_theme} {'Use Image ' + str(len(ingr)) + ' as the exact background location. ' if any(isinstance(x, str) and 'локации' in x for x in ingr) else ''}Medium shot, eye-level. Golden afternoon light, joy. {ST}",
        f"{prompt_theme} {'Use Image ' + str(len(ingr)) + ' as the exact background location. ' if any(isinstance(x, str) and 'локации' in x for x in ingr) else ''}Medium close-up, eye-level. Warm light, relief. {ST}",
        f"{prompt_theme} {'Use Image ' + str(len(ingr)) + ' as the exact background location. ' if any(isinstance(x, str) and 'локации' in x for x in ingr) else ''}Medium shot, eye-level. Afternoon sun, peaceful. {ST}",
    ))

# S20 — Amin + Aya doubts (+8)
for suffix, desc, ingr, prompt_theme in [
    ("S20_E", "Establishing: комната Амина ночью. Лампа. Фотографии подземного города.", [L("amin_room")], "A bedroom at night — desk lamp on, printed photographs of underground chambers spread on the desk. Carved stone, ancient arches, the inscription. Quiet contemplation atmosphere."),
    ("S20_F", "Амин рассматривает фото надписи. Проводит пальцем по контуру букв.", [A, L("amin_room")], "The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, sits at his desk, tracing the outline of ancient carved letters in a photograph — connecting with the past through touch."),
    ("S20_G", "Ая заходит. «Не спишь?» Садится рядом.", [Y, A, L("amin_room")], "First, the exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, appears at the bedroom door, looking in. Then, the exact character in a grey hoodie from Image 2, looks up from the photographs. She enters, sits beside him."),
    ("S20_H", "Ая: «Джамиль ни разу не назвал имя. Того, кто ему угрожал.»", [Y, L("amin_room")], "The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, speaks in the quiet bedroom, face thoughtful — pointing out the omission, the thing nobody else noticed."),
    ("S20_I", "Амин: «Заметил.» Тишина. «Может, не хочет нас впутывать.»", [A, L("amin_room")], "The exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, sits in the lamplight, acknowledging his sister's observation — he noticed too, and he's been thinking about it."),
    ("S20_J", "Ая: «Правда — это не только что человек говорит. Это ещё и то, о чём он молчит.»", [Y, L("amin_room")], "The exact character in a pink dress and dark navy striped hijab from Image 1, preserving identical facial features and proportions, speaks with quiet wisdom in the bedroom lamplight — offering a truth about truth itself."),
    ("S20_K", "Вид из окна: дом Джамиля. Свет в окне. Силуэт смотрит куда-то далеко.", [L("amin_room")], "View through a bedroom window at night — the neighboring house with one lit window, a silhouette standing inside looking not at the street but into the distance. A man with secrets still unshared."),
    ("S20_L", "Крупный план: на столе Джамиля — тетрадь, которую он показывал. И рядом — вторая. С маленьким замком. Никому не показывал.", [L("amin_room")], "Through a window at night — on a distant table, visible in lamplight: an open notebook (the familiar one), and beside it — a thinner notebook with a small lock. The one never shown. Never mentioned. The final mystery."),
]:
    EXT_CLIPS.append(raw(suffix, "S20", desc, ingr,
        f"{prompt_theme} {'Use Image ' + str(len(ingr)) + ' as the exact background location. ' if any(isinstance(x, str) and 'локации' in x for x in ingr) else ''}Medium shot, eye-level. Night lamp light, intimate. {ST}",
        f"{prompt_theme} {'Use Image ' + str(len(ingr)) + ' as the exact background location. ' if any(isinstance(x, str) and 'локации' in x for x in ingr) else ''}Medium close-up, eye-level. Warm lamplight, thoughtful. {ST}",
        f"{prompt_theme} {'Use Image ' + str(len(ingr)) + ' as the exact background location. ' if any(isinstance(x, str) and 'локации' in x for x in ingr) else ''}Medium shot, eye-level. Evening light, reflective. {ST}",
        f"{prompt_theme} {'Use Image ' + str(len(ingr)) + ' as the exact background location. ' if any(isinstance(x, str) and 'локации' in x for x in ingr) else ''}Medium shot, eye-level. Lamp glow, contemplative. {ST}",
    ))

# S21 — Tako's ending + Simba (+8)
for suffix, desc, ingr, prompt_theme in [
    ("S21_E", "Establishing: комната Тако ночью. Темно. Тако лежит в кровати.", [T, L("tako_room")], "The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, lies in bed in a dark room, blanket up to his chin, eyes open, staring at the ceiling — debriefing himself in the quiet."),
    ("S21_F", "Тако бормочет: «Молния завершила операцию. Подземный город обнаружен.»", [T, L("tako_room")], "The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, lies in bed whispering to himself, eyes on the ceiling — running through the mission debrief, lips barely moving, the smallest operative reviewing the biggest case."),
    ("S21_G", "Тако: «Но главный не раскрыт. Рашид Камаль. Призрак.»", [T, L("tako_room")], "The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, lies in the dark room, expression shifting to determination — one loose end, one ghost, one name without a face. Unfinished business."),
    ("S21_H", "Тако: «Тако его найдёт. Рано или поздно.»", [T, L("tako_room")], "The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, turns his head on the pillow, jaw set with quiet conviction — the promise of a seven-year-old who means every word."),
    ("S21_I", "Тако: «Но не сегодня. Сегодня Молния отдыхает. Заслуженно.»", [T, L("tako_room")], "The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, rolls onto his side, pulling the blanket up, eyes closing — the operative standing down, earned rest. A small smile."),
    ("S21_J", "Тако засыпает. Тишина. Лунный свет через окно.", [T, L("tako_room")], "The exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, lies still in bed, breathing evened out, asleep — moonlight from the window painting a stripe across the peaceful face of a sleeping child."),
    ("S21_K", "Симба у ворот Джамиля. Лежит. Уши торчком. Глаза открыты. Не спит. Сторожит.", [SB, L("jamil_house_front")], "The exact animal from Image 1, preserving identical facial features and proportions, lies at the gate of the old house at night, ears erect, eyes open and alert — moonlight on fur, the street empty and quiet, but the guardian never sleeps. Watching. Protecting."),
    ("S21_L", "Затемнение. Конец. Лунный свет на пустой улице.", [L("night_street")], "A quiet residential street at night — moonlight flooding the empty road, houses sleeping, a single streetlight, deep blue shadows. The end of a story. The beginning of the next. Peace, but not forever."),
]:
    EXT_CLIPS.append(raw(suffix, "S21", desc, ingr,
        f"{prompt_theme} {'Use Image ' + str(len(ingr)) + ' as the exact background location. ' if any(isinstance(x, str) and 'локации' in x for x in ingr) else ''}Medium shot, eye-level. {'Night moonlight' if 'night' in prompt_theme.lower() or 'moon' in prompt_theme.lower() or 'dark' in prompt_theme.lower() else 'Warm lamp light'}. {ST}",
        f"{prompt_theme} {'Use Image ' + str(len(ingr)) + ' as the exact background location. ' if any(isinstance(x, str) and 'локации' in x for x in ingr) else ''}Medium close-up, eye-level. Night atmosphere. {ST}",
        f"{prompt_theme} {'Use Image ' + str(len(ingr)) + ' as the exact background location. ' if any(isinstance(x, str) and 'локации' in x for x in ingr) else ''}Medium shot, eye-level. Cool moonlight, quiet. {ST}",
        f"{prompt_theme} {'Use Image ' + str(len(ingr)) + ' as the exact background location. ' if any(isinstance(x, str) and 'локации' in x for x in ingr) else ''}Medium shot, eye-level. Night tones, cinematic. {ST}",
    ))

# Final count
print(f"Extension clips defined: {len(EXT_CLIPS)}")
