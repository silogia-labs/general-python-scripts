// === CONFIG: map Quizify text -> internal field keys & types ===
// field_type: "single" or "multi_select"
const QUESTION_CONFIG = {
    "Rango de edad": { field: "age_range", field_type: "single" },
    "¿Fuiste asignada mujer al nacer?": { field: "assigned_female_at_birth", field_type: "single" },
    "Reflexiona, ¿has presentado alguno de estos signos de alarma?": {
        field: "red_flags_answer",
        tagsField: "red_flags_tag",
        field_type: "multi_select"
    },
    "Calidad de sueño": { field: "sleep_quality", field_type: "single" },
    "Estrés percibido (0-10)": { field: "stress_level", field_type: "single" },
    "Intensidad del dolor (0-10)": { field: "pain_intensity", field_type: "single" },
    "Historia obstétrica": { field: "pregnancy_history", field_type: "single" },
    "Tipo de parto": { field: "delivery_type", field_type: "single" },
    "Meses desde el parto": { field: "postpartum_months", field_type: "single" },
    "Ciclo menstrual": { field: "menstrual_cycle", field_type: "single" },
    "Perimenopausia/Menopausia": { field: "menopause_status", field_type: "single" },
    "Ubicación del dolor": { field: "pain_location", field_type: "single" },
    "Duración del problema": { field: "pain_duration", field_type: "single" },
    "¿Presentas alguno de estos síntomas de piso pélvico?": {
        field: "pelvic_floor_symptoms",
        field_type: "multi_select"
    },
    "Disparadores de crisis": {
        field: "flare_triggers",
        field_type: "multi_select"
    },
    "Limitaciones funcionales": {
        field: "functional_limitations",
        field_type: "multi_select"
    },
    "Mi objetivo principal es...": {
        field: "primary_goal",
        tagsField: "primary_goal_tag",
        field_type: "single"
    },
    "Nivel de deporte": { field: "sport_level", field_type: "single" },
    "Consiento que usen mis respuestas para mi resultado y recibir el plan por email.": {
        field: "consent_answer",
        tagsField: "consent_tag",
        field_type: "single"
    },
    "Tipo de Jornada laboral": { field: "work_shift_type", field_type: "single" }
};


// === HELPERS ===
function toStringArrayFromCsv(str) {
    if (!str || typeof str !== "string") return [];
    return str.split(",").map(s => s.trim()).filter(Boolean);
}

function extractAnswer(record, index, fieldType) {
    const answersKey = `answers-${index}`;
    const tagsKey = `answers-tags-${index}`;
    const answers = record[answersKey];
    const tags = record[tagsKey];

    let value;

    if (fieldType === "multi_select") {
        if (Array.isArray(answers)) {
            value = answers.map(a => a?.answer_name).filter(Boolean);
        } else if (typeof answers === "string") {
            const arr = toStringArrayFromCsv(answers);
            value = arr.length ? arr : [answers.trim()];
        } else {
            value = [];
        }
    } else {
        if (Array.isArray(answers)) {
            const names = answers.map(a => a?.answer_name).filter(Boolean);
            value = names.length > 1 ? names.join(", ") : names[0] || null;
        } else if (typeof answers === "string") {
            value = answers;
        } else {
            value = answers != null ? String(answers) : null;
        }
    }

    return {
        value,
        tags: (typeof tags === "string" && tags.length > 0) ? tags : null
    };
}


// === MAIN ===
const raw = input.quiz_response;
const record = Array.isArray(raw) ? raw[0] : raw;

// Base output
const output = {
    email: record.email || null,
    firstName: record.firstName || null,
    lastName: record.lastName || null,
    phone: record.phone || null,
    status: record.status || null,
    statusDate: record.statusDate || null,
    quiz_title: record.quiz_title || null,
    product_recommendation: record["product-recommendation"] || null,
    title: record.title || null,
    type_page_url: record["type-page-url"] || null,
    tags: [] // final merged tags go here
};


// === PROCESS QUESTIONS ===
Object.keys(record).forEach(key => {
    const match = key.match(/^question-(\d+)$/);
    if (!match) return;

    const index = match[1];
    const questionText = record[key];
    const cfg = QUESTION_CONFIG[questionText];
    if (!cfg) return;

    const { field, tagsField, field_type } = cfg;
    const { value, tags } = extractAnswer(record, index, field_type);

    // map main
    output[field] = value;

    // map raw tags from Quizify
    if (tags) output.tags.push(tags);

    // mapped tag field
    if (tagsField && tags) output[tagsField] = tags;
});


// === DERIVED TAGS LOGIC ===
function add(tag) {
    if (!output.tags.includes(tag)) output.tags.push(tag);
}

function process_multi_select_tag(answer_array, noneValue, tag_name) {
    output[tag_name] = false;
    const has_value = answer_array.length == 1 && answer_array[0] != noneValue;
    if (has_value) {
        add(tag_name);
        output[tag_name] = true;
    }
}

function process_filter_tag(answer_value, filter_value, tag_name) {
    const falg_name = `is_${tag_name}`;
    output[falg_name] = false;
    const has_value = answer_value && answer_value.toLowerCase().includes(filter_value);
    if (has_value) {
        add(tag_name);
        output[falg_name] = true;
    }
}

process_multi_select_tag(output.red_flags_answer, "Ninguno", "has_red_flags")
process_multi_select_tag(output.flare_triggers, "Ninguno", "has_triggers")
process_multi_select_tag(output.functional_limitations, "Ninguna", "has_limitations")
process_multi_select_tag(output.pelvic_floor_symptoms, "Ninguno", "has_pelvic_symptoms")

process_filter_tag(output.sport_level, "alto", "athlete")
process_filter_tag(output.work_shift_type, "hogar", "hogar")
process_filter_tag(output.menstrual_cycle, "menstrual", "menstrual")
process_filter_tag(output.pregnancy_history, "postpartum", "postpartum")
process_filter_tag(output.menopause_status, "peri", "peri_menu")

// Consent
if (output.consent_answer && output.consent_answer.toLowerCase().includes("sí")) {
    add("consent_given");
    output["consent_given"] = true
}

// Deduplicate
output.tags = [...new Set(output.tags)];


if (output.email.toLowerCase().includes("silverpaezp") || output.email.toLowerCase().includes("iranipaez")) {
    let min = 1000;
    let max = 9999;
    let rand = Math.floor(Math.random() * (max - min + 1)) + min;
    let email_split = output.email.split('@');
    output.email = email_split[0] + '+' + rand + '@' + email_split[1];
}

return output;
