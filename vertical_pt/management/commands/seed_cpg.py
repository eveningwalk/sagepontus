"""Seed APTA CPG knowledge chunks into KnowledgeChunk table.

Usage:
    python manage.py seed_cpg           # seed text only (no embeddings)
    python manage.py seed_cpg --embed   # seed + generate Gemini embeddings
    python manage.py seed_cpg --clear   # wipe existing CPG chunks first
"""
from django.core.management.base import BaseCommand
from vertical_pt.models import KnowledgeChunk

CPG_CHUNKS = [
    # ── Low Back Pain ──────────────────────────────────────────────────────────
    {
        "title": "APTA CPG: Low Back Pain — Clinical Presentation & Red Flags",
        "condition": "low back pain",
        "content": (
            "Therapists should screen for serious pathology (red flags) in patients presenting with LBP. "
            "Red flags include: age >50 or <20, history of cancer, unexplained weight loss, fever, "
            "failure to improve with conservative care after 4–6 weeks, pain at rest or nocturnal pain, "
            "bowel/bladder dysfunction, saddle anesthesia, bilateral neurological deficits, and "
            "history of IV drug use or immunosuppression. Patients presenting with red flags should be "
            "referred to appropriate medical personnel without delay."
        ),
        "meta": {"section": "Examination", "url": "https://www.jospt.org/doi/10.2519/jospt.2021.0301"},
    },
    {
        "title": "APTA CPG: Low Back Pain — Cauda Equina Syndrome",
        "condition": "cauda equina",
        "content": (
            "Cauda equina syndrome (CES) is a surgical emergency characterized by saddle anesthesia, "
            "bladder and/or bowel dysfunction, bilateral leg weakness, and severe LBP. "
            "Physical therapists must immediately refer patients with suspected CES to emergency services. "
            "The hallmark symptoms include urinary retention or incontinence, fecal incontinence, "
            "perianal/perineal numbness, and progressive bilateral lower extremity weakness. "
            "Delay in surgical decompression beyond 24–48 hours significantly worsens outcomes. "
            "APTA guidelines recommend that PTs document all neurological findings and initiate "
            "emergency referral when CES is suspected, without waiting for imaging confirmation."
        ),
        "meta": {"section": "Red Flags", "url": "https://www.jospt.org/doi/10.2519/jospt.2021.0301"},
    },
    {
        "title": "APTA CPG: Low Back Pain — Spinal Fracture",
        "condition": "fracture",
        "content": (
            "Risk factors for vertebral fracture include: age >70, female sex, corticosteroid use, "
            "significant trauma, osteoporosis diagnosis, and prior fragility fracture. "
            "Clinical indicators include severe localized spinal tenderness, inability to bear weight, "
            "and pain that worsens with percussion over the spinous processes. "
            "Physical therapists should refer patients with suspected vertebral fracture for imaging "
            "(plain radiograph as first line) before initiating manual therapy or exercise interventions. "
            "APTA guidelines recommend risk stratification using the Ottawa Back Rules."
        ),
        "meta": {"section": "Red Flags", "url": "https://www.jospt.org/doi/10.2519/jospt.2021.0301"},
    },
    {
        "title": "APTA CPG: Low Back Pain — Spinal Malignancy",
        "condition": "malignancy",
        "content": (
            "Red flags for spinal malignancy include: prior history of cancer (especially breast, lung, "
            "prostate, kidney, thyroid), unexplained weight loss >10 lbs in 6 months, age >50, "
            "failure to improve with 4–6 weeks of conservative care, and pain that is constant, "
            "progressive, and unrelieved by rest or position change. "
            "Nocturnal pain awakening the patient from sleep is a significant clinical indicator. "
            "Physical therapists should refer patients with multiple malignancy red flags for "
            "urgent medical evaluation and plain radiographs or MRI as indicated."
        ),
        "meta": {"section": "Red Flags", "url": "https://www.jospt.org/doi/10.2519/jospt.2021.0301"},
    },
    {
        "title": "APTA CPG: Low Back Pain — Spinal Infection",
        "condition": "infection",
        "content": (
            "Spinal infection (discitis, osteomyelitis, epidural abscess) red flags include: "
            "fever >38°C, recent bacterial infection (UTI, skin infection, dental procedure), "
            "IV drug use, immunocompromised status (HIV, diabetes, corticosteroid use), "
            "recent spinal surgery or procedure, and severe unrelenting pain unresponsive to rest. "
            "Epidural abscess is a surgical emergency; delay in treatment can result in permanent "
            "neurological deficit. APTA guidelines recommend immediate medical referral when "
            "spinal infection is suspected, with ESR, CRP, and CBC as initial laboratory workup."
        ),
        "meta": {"section": "Red Flags", "url": "https://www.jospt.org/doi/10.2519/jospt.2021.0301"},
    },
    {
        "title": "APTA CPG: Low Back Pain — Abdominal Aortic Aneurysm",
        "condition": "vascular",
        "content": (
            "Abdominal aortic aneurysm (AAA) must be considered in patients >60 years presenting with "
            "LBP, particularly males with history of smoking or hypertension. "
            "Key differentiating features: pulsatile abdominal mass, pain radiating to flank or groin, "
            "pain unaffected by spinal movement or position, and abdominal bruit on auscultation. "
            "Symptomatic AAA is a life-threatening emergency requiring immediate vascular surgery referral. "
            "Physical therapists should avoid abdominal or lumbar manipulation in patients with suspected AAA "
            "and arrange emergency transport immediately."
        ),
        "meta": {"section": "Red Flags", "url": "https://www.jospt.org/doi/10.2519/jospt.2021.0301"},
    },
    {
        "title": "APTA CPG: Low Back Pain — Inflammatory Spondyloarthropathy",
        "condition": "inflammatory",
        "content": (
            "Inflammatory back pain (ankylosing spondylitis, axial spondyloarthropathy) is distinguished "
            "from mechanical LBP by: onset before age 40, insidious onset, morning stiffness >45 minutes "
            "that improves with exercise but not rest, alternating buttock pain, nocturnal pain in second "
            "half of night, and improvement with NSAIDs. "
            "The Assessment of SpondyloArthritis international Society (ASAS) criteria requires referral "
            "to rheumatology when ≥3 features are present in patients with chronic LBP >3 months. "
            "Physical therapists play a key role in early identification and should refer for HLA-B27 "
            "testing and rheumatological evaluation."
        ),
        "meta": {"section": "Red Flags", "url": "https://www.jospt.org/doi/10.2519/jospt.2021.0301"},
    },
    {
        "title": "APTA CPG: Low Back Pain — Direct Access Screening Responsibility",
        "condition": "low back pain",
        "content": (
            "Under direct access, physical therapists bear full responsibility for medical screening "
            "and differential diagnosis. The APTA Clinical Practice Guideline for Low Back Pain "
            "mandates that PTs perform a thorough systems review and screen for red flags at every "
            "initial evaluation and when symptoms change. Documentation must reflect the screening "
            "process and clinical reasoning for referral or continued PT management. "
            "Failure to identify and refer red flag conditions constitutes a breach of the standard "
            "of care and may result in professional liability."
        ),
        "meta": {"section": "Direct Access", "url": "https://www.jospt.org/doi/10.2519/jospt.2021.0301"},
    },
    # ── Neck Pain ─────────────────────────────────────────────────────────────
    {
        "title": "APTA CPG: Neck Pain — Red Flags & Screening",
        "condition": "neck pain",
        "content": (
            "Physical therapists managing neck pain must screen for serious pathology including: "
            "cervical myelopathy (bilateral UE/LE numbness, gait disturbance, hand clumsiness, "
            "hyperreflexia, positive Hoffman's sign), cervical artery dysfunction (dizziness, "
            "diplopia, dysphagia, dysarthria, drop attacks — 5 Ds + 3 Ns), "
            "upper cervical instability post-trauma (Sharp-Purser test, alar ligament test), "
            "and vertebral fracture in high-velocity trauma or osteoporotic patients. "
            "Patients with suspected cervical myelopathy should be referred for MRI and orthopedic "
            "or neurosurgical consultation."
        ),
        "meta": {"section": "Examination", "url": "https://www.jospt.org/doi/10.2519/jospt.2017.0302"},
    },
    # ── Knee ──────────────────────────────────────────────────────────────────
    {
        "title": "APTA CPG: Knee Pain / OA — Examination & Referral",
        "condition": "knee",
        "content": (
            "For knee osteoarthritis, APTA guidelines recommend referral to orthopedics when: "
            "conservative PT management (≥6 weeks of supervised exercise, pain education, and "
            "weight management counseling) fails to achieve meaningful improvement (KOOS MCID = 10 points), "
            "signs of acute hemarthrosis or septic arthritis are present (joint effusion, warmth, fever), "
            "or significant mechanical symptoms (locking, giving way) suggest internal derangement "
            "requiring surgical evaluation. "
            "Refer for urgent evaluation when septic arthritis is suspected — joint aspiration and "
            "culture are required within hours to prevent joint destruction."
        ),
        "meta": {"section": "Intervention", "url": "https://www.jospt.org/doi/10.2519/jospt.2018.0301"},
    },
    # ── Shoulder ──────────────────────────────────────────────────────────────
    {
        "title": "APTA CPG: Shoulder Pain — Red Flags & Referral",
        "condition": "shoulder",
        "content": (
            "APTA guidelines for shoulder pain require PTs to screen for: "
            "referred pain from cardiac origin (left shoulder pain with exertional component, "
            "diaphoresis, nausea — refer to emergency services immediately), "
            "cervical radiculopathy vs. primary shoulder pathology (Spurling's test, ULTT), "
            "rotator cuff tear in patients >60 with acute onset weakness after fall (refer for ultrasound/MRI), "
            "and glenohumeral instability in young athletes (refer for surgical evaluation if "
            "conservative care fails after 3–6 months). "
            "Frozen shoulder (adhesive capsulitis) MCID for pain-free range of motion: "
            "clinically meaningful improvement defined as ≥30° gain in external rotation."
        ),
        "meta": {"section": "Examination", "url": "https://www.jospt.org/doi/10.2519/jospt.2019.0302"},
    },
]


class Command(BaseCommand):
    help = "Seed APTA CPG knowledge chunks. Use --embed to generate Gemini embeddings."

    def add_arguments(self, parser):
        parser.add_argument("--embed", action="store_true", help="Generate embeddings via Gemini API")
        parser.add_argument("--clear", action="store_true", help="Clear existing CPG chunks before seeding")

    def handle(self, *args, **options):
        if options["clear"]:
            deleted, _ = KnowledgeChunk.objects.filter(source="apta_cpg").delete()
            self.stdout.write(f"Cleared {deleted} existing CPG chunks.")

        from vertical_pt.engine.rag import embed_text

        created = 0
        for chunk in CPG_CHUNKS:
            embedding = []
            if options["embed"]:
                self.stdout.write(f"  Embedding: {chunk['title'][:60]}...")
                embedding = embed_text(chunk["content"])

            obj, is_new = KnowledgeChunk.objects.update_or_create(
                source="apta_cpg",
                title=chunk["title"],
                defaults={
                    "condition": chunk["condition"],
                    "content":   chunk["content"],
                    "meta":      chunk["meta"],
                    **({"embedding": embedding} if embedding else {}),
                },
            )
            if is_new:
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. {created} new / {len(CPG_CHUNKS) - created} updated CPG chunks. "
            f"{'Embeddings generated.' if options['embed'] else 'Run with --embed to add embeddings.'}"
        ))
