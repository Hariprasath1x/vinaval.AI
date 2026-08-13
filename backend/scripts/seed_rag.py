"""
Seed the ChromaDB vector store with curated Tamil Nadu syllabus content.
Run once (or any time you add new material):

  cd backend
  python scripts/seed_rag.py

Collections are keyed as "<exam>_<subject>" (e.g. "neet_physics").
Each chunk is stored with metadata so the retriever can cite it.
"""
from __future__ import annotations
import sys
import os

# Allow imports from the parent package
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.vector_store import get_vector_store

# ── Seed Data ────────────────────────────────────────────────────────────────
# Format: list of (exam, subject, topic, chunk_text) tuples.
# Add more entries here as you build out the content library.

SEED_DATA: list[tuple[str, str, str, str]] = [

    # ── NEET · Physics ──────────────────────────────────────────────────────
    ("NEET", "Physics", "Newton's Laws of Motion",
     """Newton's First Law (Law of Inertia): Every object continues to be in its state of rest or uniform 
     motion along a straight line unless acted upon by an external unbalanced force. Inertia is the tendency 
     of a body to resist changes to its state of motion. More massive objects have greater inertia."""),

    ("NEET", "Physics", "Newton's Laws of Motion",
     """Newton's Second Law: The rate of change of momentum of an object is proportional to the net external 
     force applied and takes place in the direction of the force. Mathematically: F = ma, where F is force 
     in Newtons (N), m is mass in kg, and a is acceleration in m/s². If mass is constant, F = ma directly."""),

    ("NEET", "Physics", "Newton's Laws of Motion",
     """Newton's Third Law: For every action there is an equal and opposite reaction. Forces always occur 
     in pairs — action-reaction pairs. Example: When a gun fires a bullet, the bullet moves forward 
     (action) and the gun recoils backward (reaction). These forces act on different bodies."""),

    ("NEET", "Physics", "Work, Energy and Power",
     """Work done by a constant force: W = F·d·cosθ, where θ is the angle between force and displacement. 
     Work is a scalar quantity measured in Joules (J). Work done is zero when force is perpendicular to 
     displacement (e.g., centripetal force does no work). Work can be positive, negative, or zero."""),

    ("NEET", "Physics", "Work, Energy and Power",
     """Kinetic Energy (KE) = ½mv². The work-energy theorem states that the net work done on an object 
     equals the change in its kinetic energy: W_net = ΔKE. Potential Energy due to gravity: PE = mgh, 
     where h is height above reference. Conservation of Energy: total mechanical energy E = KE + PE is 
     constant in the absence of non-conservative forces."""),

    ("NEET", "Physics", "Gravitation",
     """Newton's Law of Universal Gravitation: Every particle attracts every other particle with a force 
     F = G·m1·m2 / r², where G = 6.674×10⁻¹¹ N·m²/kg². The force is attractive, acts along the line 
     joining the two masses, and is inversely proportional to the square of the distance between them."""),

    ("NEET", "Physics", "Gravitation",
     """Acceleration due to gravity: g = GM/R² at Earth's surface (g ≈ 9.8 m/s²). Variation of g: 
     - With altitude h: g' = g(1 - 2h/R) for small h.
     - With depth d: g' = g(1 - d/R).
     - At poles g is greatest; at equator g is least (due to Earth's shape and rotation).
     Escape velocity: v_e = √(2gR) ≈ 11.2 km/s for Earth."""),

    # ── NEET · Chemistry ────────────────────────────────────────────────────
    ("NEET", "Chemistry", "Atomic Structure",
     """Bohr's Model of Hydrogen Atom: Electrons revolve in fixed circular orbits (stationary states) 
     around the nucleus. Energy of nth orbit: E_n = -13.6/n² eV. Radius of nth orbit: r_n = 0.529n² Å. 
     When an electron jumps from higher to lower orbit, it emits a photon: E = hν = E_higher - E_lower."""),

    ("NEET", "Chemistry", "Atomic Structure",
     """Quantum Numbers: (1) Principal quantum number (n): determines energy and size of orbital (n = 1,2,3,...). 
     (2) Azimuthal quantum number (l): determines shape (l = 0 to n-1; s,p,d,f). 
     (3) Magnetic quantum number (ml): determines orientation (-l to +l). 
     (4) Spin quantum number (ms): +½ or -½. Pauli's exclusion: no two electrons can have the same four 
     quantum numbers. Aufbau principle: fill orbitals in increasing energy order."""),

    ("NEET", "Chemistry", "Chemical Bonding",
     """Ionic Bond: Formed by complete transfer of electrons from metal to non-metal. Example: NaCl — Na 
     loses 1 electron to become Na⁺ and Cl gains 1 electron to become Cl⁻. Properties: high melting point, 
     conducts electricity in molten/aqueous state, soluble in polar solvents like water."""),

    ("NEET", "Chemistry", "Chemical Bonding",
     """Covalent Bond: Formed by sharing of electrons between non-metals. Lewis structures show shared pairs 
     as lines. Bond order = (bonding electrons - antibonding electrons) / 2. 
     VSEPR Theory predicts shapes: linear (2 bond pairs), trigonal planar (3), tetrahedral (4), 
     trigonal bipyramidal (5), octahedral (6). Lone pairs repel more than bonding pairs."""),

    # ── NEET · Biology (Botany) ─────────────────────────────────────────────
    ("NEET", "Botany", "Cell Structure",
     """Cell Theory (Schleiden, Schwann, Virchow): (1) All living organisms are made of cells. 
     (2) The cell is the basic structural and functional unit of life. 
     (3) All cells arise from pre-existing cells. Prokaryotic cells have no membrane-bound nucleus; 
     eukaryotic cells have a well-defined nucleus. Plant cells have cell wall (cellulose), chloroplasts, 
     and central vacuole which animal cells lack."""),

    ("NEET", "Botany", "Cell Structure",
     """Mitochondria (powerhouse of cell): double-membrane organelle; inner membrane is folded into cristae 
     to increase surface area for ATP synthesis. ATP is produced by oxidative phosphorylation. 
     Chloroplasts (found only in plant cells): double-membrane; contain thylakoids stacked into grana 
     where light reactions occur, and stroma where dark reactions (Calvin cycle) occur."""),

    ("NEET", "Botany", "Photosynthesis",
     """Photosynthesis: 6CO₂ + 6H₂O + light energy → C₆H₁₂O₆ + 6O₂. 
     Two stages: (1) Light-dependent reactions in thylakoid membrane — water is split (photolysis), 
     O₂ is released, ATP and NADPH are produced. (2) Calvin Cycle (light-independent) in stroma — 
     CO₂ is fixed using ATP and NADPH to produce G3P (glyceraldehyde-3-phosphate), which is used to 
     make glucose."""),

    # ── NEET · Biology (Zoology) ────────────────────────────────────────────
    ("NEET", "Zoology", "Human Physiology",
     """Human Digestive System: Mouth (amylase begins starch digestion) → Oesophagus (peristalsis) → 
     Stomach (pepsin + HCl digest proteins; churning) → Small Intestine (main site of digestion and 
     absorption; villi and microvilli increase surface area) → Large Intestine (water absorption; 
     formation of faeces) → Rectum → Anus."""),

    ("NEET", "Zoology", "Human Physiology",
     """Human Heart: 4 chambers — 2 atria (receive blood) and 2 ventricles (pump blood). 
     Right side: deoxygenated blood → lungs (pulmonary circulation). 
     Left side: oxygenated blood → body (systemic circulation). 
     SA node (pacemaker) generates impulse → AV node → Bundle of His → Purkinje fibres. 
     Normal heart rate: 72 beats/min. Blood pressure: 120/80 mmHg (systolic/diastolic)."""),

    # ── TNPSC · History ─────────────────────────────────────────────────────
    ("TNPSC", "History", "Indus Valley Civilisation",
     """Indus Valley Civilisation (IVC) / Harappan Civilisation: Flourished ca. 3300–1300 BCE in the 
     Indian subcontinent, primarily in present-day Pakistan and northwest India. Major sites: Harappa 
     (Punjab), Mohenjo-daro (Sindh), Lothal (Gujarat), Kalibangan (Rajasthan), Dholavira (Gujarat). 
     Known for: town planning with grid layout, covered drainage, standardised weights and measures, 
     pictographic script (undeciphered), baked brick structures, and advanced sanitation."""),

    ("TNPSC", "History", "Sangam Age",
     """Sangam Age (ca. 300 BCE–300 CE): refers to the period of ancient Tamil literature compiled in 
     three academies (Sangams) in Madurai. Major Sangam texts: Tolkappiyam (grammar), Eight Anthologies 
     (Ettuthokai), Ten Idylls (Pattupattu), and the Eighteen Minor Works (Pathinenkilkanakku). 
     Three chief kingdoms: Cheras (capital Vanji, Kerala), Cholas (capital Uraiyur, Tamil Nadu), 
     Pandyas (capital Madurai, Tamil Nadu)."""),

    ("TNPSC", "History", "Mughal Empire",
     """Mughal Empire (1526–1857): Founded by Babur after the First Battle of Panipat (1526) against 
     Ibrahim Lodi. Key rulers: Humayun, Akbar (greatest — Din-i-Ilahi, Todarmal's revenue system, 
     Navratnas), Jahangir, Shah Jahan (Taj Mahal, Red Fort), Aurangzeb (Alamgir — Jizya reimposed, 
     empire expanded but weakened due to Deccan wars). The Mughal miniature painting style blended 
     Persian and Indian traditions."""),

    # ── TNPSC · Geography ───────────────────────────────────────────────────
    ("TNPSC", "Geography", "Indian Rivers",
     """Major River Systems of India: 
     Himalayan Rivers (perennial — fed by glaciers and monsoon): Indus, Ganga, Brahmaputra and their 
     tributaries. Ganga originates from Gangotri glacier; flows 2525 km; joins Bay of Bengal. 
     Peninsular Rivers (seasonal — depend on monsoon): Godavari (largest peninsular river), Krishna, 
     Kaveri, Narmada (flows westward into Arabian Sea), Tapti. Rivers are crucial for irrigation, 
     hydroelectric power, and transportation."""),

    ("TNPSC", "Geography", "Tamil Nadu Geography",
     """Tamil Nadu: Area — 130,058 km² (11th largest state). Capital — Chennai. Major rivers: Kaveri, 
     Vaigai, Palar, Tamiraparani. Western Ghats (Sahyadri) on western border. Eastern Ghats run 
     parallel to the east coast. Highest peak in TN: Doddabetta (2637 m, Nilgiris). 
     Major crops: paddy, sugarcane, bananas, cotton, groundnut. Coromandel Coast gets rainfall mainly 
     from the northeast monsoon (Oct–Dec)."""),

    ("TNPSC", "Geography", "Climate of India",
     """Indian Climate is governed by the monsoon. Two monsoon seasons: 
     (1) Southwest Monsoon (June–September) — brings rain to most of India; windward side of Western 
     Ghats gets heavy rainfall (Malabar Coast); leeward side is rain shadow (Deccan Plateau). 
     (2) Northeast Monsoon (October–December) — brings rain to Tamil Nadu and parts of Andhra Pradesh. 
     Tropical cyclones are common in Bay of Bengal during October–November."""),

    # ── TNPSC · Polity ──────────────────────────────────────────────────────
    ("TNPSC", "Polity", "Indian Constitution",
     """The Indian Constitution came into effect on 26 January 1950. It is the longest written 
     constitution in the world. Key features: federal with unitary bias, parliamentary democracy, 
     fundamental rights (Part III), directive principles (Part IV), independent judiciary, 
     single citizenship. Drafted by the Constituent Assembly under the chairmanship of Dr. B.R. Ambedkar 
     (Chairman of Drafting Committee). Preamble declares India a Sovereign, Socialist, Secular, 
     Democratic Republic."""),

    ("TNPSC", "Polity", "Fundamental Rights",
     """Fundamental Rights (Articles 12–35) are guaranteed by the Indian Constitution. Six categories: 
     (1) Right to Equality (Art. 14–18), (2) Right to Freedom (Art. 19–22), (3) Right against 
     Exploitation (Art. 23–24), (4) Right to Freedom of Religion (Art. 25–28), 
     (5) Cultural and Educational Rights (Art. 29–30), (6) Right to Constitutional Remedies (Art. 32) 
     — called 'heart and soul of the Constitution' by Ambedkar. Right to Property removed by 44th Amendment."""),

    # ── TNPSC · Economics ───────────────────────────────────────────────────
    ("TNPSC", "Economics", "Indian Economy Basics",
     """India's Economic Planning: Five-Year Plans were formulated by the Planning Commission (set up 1950) 
     under the chairmanship of PM. NITI Aayog replaced the Planning Commission in 2015. 
     India follows a Mixed Economy — both public and private sectors coexist. GDP (Gross Domestic Product) 
     measures the total value of goods and services produced within India's borders in one year. 
     India is the 5th largest economy by nominal GDP and 3rd largest by PPP."""),

    ("TNPSC", "Economics", "Banking",
     """Reserve Bank of India (RBI): Central bank of India, established in 1935. Functions: issues 
     currency (except ₹1 coin/note issued by Govt), banker to government, regulates and supervises banks, 
     controls credit and money supply, manages foreign exchange. Key rates: Repo rate (rate at which RBI 
     lends to commercial banks), Reverse Repo rate (rate at which RBI borrows from banks), 
     CRR (Cash Reserve Ratio — % of deposits kept with RBI), SLR (Statutory Liquidity Ratio)."""),
]


def main():
    print(f"Seeding {len(SEED_DATA)} chunks into ChromaDB...")

    # Track per-collection progress
    counts: dict[str, int] = {}

    for idx, (exam, subject, topic, text) in enumerate(SEED_DATA):
        collection = get_vector_store().get_collection(exam, subject)
        doc_id = f"{exam}_{subject}_{idx}".lower().replace(" ", "_")

        collection.add(
            ids=[doc_id],
            documents=[text],
            metadatas=[{
                "exam": exam,
                "subject": subject,
                "topic": topic,
            }],
        )
        key = f"{exam}/{subject}"
        counts[key] = counts.get(key, 0) + 1

    print("\nSeeding complete!")
    for key, count in sorted(counts.items()):
        print(f"  [OK] {key}: {count} chunk(s)")


if __name__ == "__main__":
    main()
