const SCORE_RULES = {
    painIntensity: {
        high: 7,  // >= 7 → 2 points
        medium: 4 // >= 4 → 1 point
    },
    painDuration: {
        highPatterns: [">12", "> 12", "más de 12", "12+", "mas de 12"],
        mediumPatterns: ["6–12", "6-12", "6 a 12", "6 a 12 meses"]
    },
    stressLevel: {
        high: 7,
        medium: 4
    },
    pelvicSymptoms: {
        mediumCount: 1, // 1–2 symptoms → 1 point
        highCount: 3    // 3+ symptoms → 2 points
    },
    functionalLimitations: {
        mediumCount: 1,
        highCount: 3
    },
    flareTriggers: {
        mediumCount: 1,
        highCount: 3
    }
};

// Sleep quality scoring by text
const SLEEP_MAP = {
    mala: 2,
    regular: 1,
    buena: 0
};

// Severity bands
const TOTAL_SCORE_LEVELS = [
    { max: 2, level: "leve" },
    { max: 5, level: "moderado" },
    { max: Infinity, level: "severo" }
];


function toNumber(value) {
    if (value == null) return 0;
    if (typeof value === "number") return value;
    const match = String(value).match(/(\d+(\.\d+)?)/);
    return match ? parseFloat(match[1]) : 0;
}

function includesAny(haystack, patterns) {
    if (!haystack) return false;
    const s = String(haystack).toLowerCase();
    return patterns.some(p => s.includes(p.toLowerCase()));
}

function scorePainIntensity(value) {
    const n = toNumber(value);
    if (n >= SCORE_RULES.painIntensity.high) return 2;
    if (n >= SCORE_RULES.painIntensity.medium) return 1;
    return 0;
}

function scorePainDuration(durationStr) {
    const s = (durationStr || "").toLowerCase();
    if (includesAny(s, SCORE_RULES.painDuration.highPatterns)) return 2;
    if (includesAny(s, SCORE_RULES.painDuration.mediumPatterns)) return 1;
    return 0;
}

function scoreCountArray(arr, rule) {
    if (!Array.isArray(arr)) return 0;
    const n = arr.length;
    if (n >= rule.highCount) return 2;
    if (n >= rule.mediumCount) return 1;
    return 0;
}

function scoreSleepQuality(sleepStr) {
    if (!sleepStr) return 0;
    const s = String(sleepStr).toLowerCase();
    if (s.includes("mala")) return SLEEP_MAP.mala;
    if (s.includes("regular")) return SLEEP_MAP.regular;
    if (s.includes("buena")) return SLEEP_MAP.buena;
    return 0;
}

function scoreStressLevel(value) {
    const n = toNumber(value);
    if (n >= SCORE_RULES.stressLevel.high) return 2;
    if (n >= SCORE_RULES.stressLevel.medium) return 1;
    return 0;
}

function classifyTotalScore(total) {
    for (const band of TOTAL_SCORE_LEVELS) {
        if (total <= band.max) return band.level;
    }
    return "unknown";
}

function hasTag(tags, target) {
    if (!Array.isArray(tags)) return false;
    return tags.includes(target);
}


// ====== NEW: CONTEXT PROFILE CALC ======
// Returns one of: "Hogar", "Doble jornada", "Minería", "Senior", "Atleta"
function calculateContextProfile({
    age_range,
    work_shift_type,
    functional_limitations,
    sport_level,
    is_athlete,
    tags
}) {
    const work = (work_shift_type || "").toLowerCase();
    const age = (age_range || "").toLowerCase();
    const sport = (sport_level || "").toLowerCase();
    const funcCount = Array.isArray(functional_limitations)
        ? functional_limitations.length
        : 0;

    // --- Detect profiles ---

    // Minería: explicit mining-related shifts
    const isMining = work.includes("minería") || work.includes("mineria");

    // Atleta: strong sports load or existing athlete tag
    const isAthleteProfile = is_athlete || hasTag(tags, "atleta");

    // Senior: older age bands
    const isSenior = age.includes("+55");

    // Hogar: home / caregiving based work
    const isHogar = work.includes("hogar");

    // Doble jornada: combines formal work + hogar/care or explicit wording
    const hasFormalJobHint =
        work.includes("oficina") ||
        work.includes("remoto") ||
        work.includes("jornada") ||
        work.includes("minería");

    const isDobleJornada =
        work.includes("doble jornada") ||
        work.includes("jornada doble") ||
        (hasFormalJobHint && isHogar) ||
        (hasFormalJobHint && funcCount >= 2); // many limitations + job → assume double load

    // --- Priority logic ---
    if (isMining) return "Minería";
    if (isAthleteProfile) return "Atleta";
    if (isSenior) return "Senior";
    if (isDobleJornada) return "Doble jornada";
    if (isHogar) return "Hogar";
    if (work.includes("remoto")) return "Reomoto";
    if (work.includes("oficina")) return "Oficinista";
    if (work.includes("nocturna")) return "Nocturno";

    // Fallback: if nothing matches, you can pick what makes more sense clinically.
    // Defaulting to "Hogar" as the base non-mining, non-athlete profile.
    return "Otro";
}


// ====== MAIN INPUT ======

// Map this input variable to the previous Code module output
const data = input.data || {};

// Shallow clone so we keep all original mapped fields
const out = { ...data };

// Normalized tags (always an array)
const tags = Array.isArray(data.tags) ? data.tags : [];


// ====== SCORE COMPONENTS ======

const score_pain_intensity = scorePainIntensity(data.pain_intensity);
const score_pain_duration = scorePainDuration(data.pain_duration);
const score_pelvic_floor = scoreCountArray(
    data.pelvic_floor_symptoms,
    SCORE_RULES.pelvicSymptoms
);
const score_functional_limitations = scoreCountArray(
    data.functional_limitations,
    SCORE_RULES.functionalLimitations
);
const score_flare_triggers = scoreCountArray(
    data.flare_triggers,
    SCORE_RULES.flareTriggers
);
const score_stress = scoreStressLevel(data.stress_level);
const score_sleep = scoreSleepQuality(data.sleep_quality || data.sleepQuality);

const score_total =
    score_pain_intensity +
    score_pain_duration +
    score_pelvic_floor +
    score_functional_limitations +
    score_flare_triggers +
    score_stress +
    score_sleep;

const score_level = classifyTotalScore(score_total);


// ====== PROFILE DETERMINATION ======

const is_postpartum = hasTag(tags, "postpartum");
const is_peri_meno = hasTag(tags, "peri_menu");
const is_menstrual = hasTag(tags, "menstrual");

// Clinical complexity profile
let profile = "profile_base";
let email_template_id = "9199514";

if (data.has_red_flags) {
    profile = "red_flags";
} else {
    if (score_level === "severo") {
        profile = "high_complexity";
        email_template_id = "9199525";
    } else if (score_level === "moderado") {
        profile = "moderate_complexity";
        email_template_id = "9199522";
    } else {
        profile = "low_complexity";
        email_template_id = "9199514";
    }
}


// Life-stage refinement (optional: mostly descriptive)
let life_stage = "life_stage_unspecified";
if (is_postpartum) {
    life_stage = "postpartum";
} else if (is_peri_meno) {
    life_stage = "peri_menopause_menopause";
} else if (is_menstrual) {
    life_stage = "menstrual_cycle_active";
}

// Activity profile (simple)
let activity_profile = "non_athlete";
if (!data.is_athlete) {
    activity_profile = "athlete";
}

// NEW: context profile (Hogar / Doble jornada / Minería / Senior / Atleta)
const context_profile = calculateContextProfile({
    age_range: data.age_range,
    work_shift_type: data.work_shift_type,
    functional_limitations: data.functional_limitations,
    sport_level: data.sport_level,
    is_athlete: data.is_athlete,
    tags
});

out.score_pain_intensity = score_pain_intensity;
out.score_pain_duration = score_pain_duration;
out.score_pelvic_floor = score_pelvic_floor;
out.score_functional_limitations = score_functional_limitations;
out.score_flare_triggers = score_flare_triggers;
out.score_stress = score_stress;
out.score_sleep = score_sleep;

out.score_total = score_total;
out.score_level = score_level;

out.profile = profile;
out.life_stage_profile = life_stage;
out.activity_profile = activity_profile;
out.context_profile = context_profile;

tags.push(life_stage)
tags.push(profile)
tags.push(activity_profile)
tags.push(context_profile)

out.email_template_id = "9199514"

if (score_level === "severo") {
    out.email_template_id = "9199525";
} else if (score_level === "moderado") {
    out.email_template_id = "9199522";
} else {
    out.email_template_id = "9199514";
}

// keep tags as-is so Airtable mapping still works
out.tags = tags;

return out;