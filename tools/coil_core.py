"""
coil_core.py
Ecuaciones puras y utilidades compartidas para microcoil_calculator.py y awg_coil_calculator.py
Sin dependencias de GUI. Todas las unidades internas en SI (metros, Henrios, Ohms, Hz).
"""

import numpy as np
from scipy.special import ellipk, ellipe

MU0 = 4 * np.pi * 1e-7  # H/m

UNITS = {
    "nm": 1e-9,
    "um": 1e-6,
    "mm": 1e-3,
    "cm": 1e-2,
    "m":  1.0,
}
UNIT_ORDER = ["nm", "um", "mm", "cm", "m"]

FREQ_UNITS = {"Hz": 1.0, "kHz": 1e3, "MHz": 1e6, "GHz": 1e9}
FREQ_ORDER = ["Hz", "kHz", "MHz", "GHz"]

MATERIALS = {
    "Cobre":    1.68e-8,
    "Oro":      2.44e-8,
    "Aluminio": 2.65e-8,
    "Plata":    1.59e-8,
    "Platino":  1.06e-7,
    "Tungsteno":5.60e-8,
}

# Coeficientes Mohan-Wheeler modificada (Mohan 1999 + Jenei 2002 para circular)
MOHAN_COEFFS = {
    "cuadrada":  (2.34, 2.75),
    "hexagonal": (2.33, 3.82),
    "octagonal": (2.25, 3.55),
    "circular":  (2.46, 2.00),
}


# =====================================================================
# Geometría
# =====================================================================

def outer_diameter(d_in, w, gap, N):
    """Diámetro exterior de la espiral planar."""
    return d_in + 2.0 * N * w + 2.0 * (N - 1) * gap


def spiral_length_circular(d_in, d_out, N):
    """Longitud de espiral arquímedes circular (m). Exacta para Arquímedes."""
    return np.pi * N * (d_in + d_out) / 2.0


def spiral_length_square(d_in, w, gap, N):
    """Longitud de espiral cuadrada. Suma de perímetros decrecientes."""
    # Lado de la espira más externa = d_out
    d_out = outer_diameter(d_in, w, gap, N)
    pitch = w + gap
    total = 0.0
    for k in range(int(np.floor(N))):
        side = d_out - 2.0 * k * pitch
        total += 4.0 * side
    # Fracción de vuelta restante
    frac = N - np.floor(N)
    if frac > 0:
        side = d_out - 2.0 * np.floor(N) * pitch
        total += 4.0 * side * frac
    return total


def awg_to_diameter(awg):
    """Diámetro de cable AWG en metros. Estándar ASTM B258."""
    d_mm = 0.127 * (92.0 ** ((36.0 - awg) / 39.0))
    return d_mm * 1e-3


# =====================================================================
# Inductancia — Microcoil planar (espiral)
# =====================================================================

def mohan_wheeler(d_in, w, gap, N, shape="cuadrada"):
    """
    Mohan-Hershenson-Boyd-Lee 1999 "Simple Accurate Expressions for Planar Spiral Inductances"
    L = K1 * mu0 * N^2 * d_avg / (1 + K2 * rho_fill)
    """
    shape = shape.lower()
    if shape not in MOHAN_COEFFS:
        shape = "cuadrada"
    K1, K2 = MOHAN_COEFFS[shape]
    d_out = outer_diameter(d_in, w, gap, N)
    d_avg = (d_out + d_in) / 2.0
    rho_fill = (d_out - d_in) / (d_out + d_in) if (d_out + d_in) > 0 else 0
    L = K1 * MU0 * (N ** 2) * d_avg / (1.0 + K2 * rho_fill)
    return L


def _segment_self_L(length, w, t):
    """
    Autoinductancia de un segmento recto rectangular (Grover/Greenhouse).
    L_self = (mu0/2pi) * length * [ ln(2*length/(w+t)) + 0.5 + (w+t)/(3*length) ]
    """
    if length <= 0:
        return 0.0
    arg = 2.0 * length / (w + t)
    return (MU0 / (2.0 * np.pi)) * length * (np.log(arg) + 0.5 + (w + t) / (3.0 * length))


def _segment_mutual_parallel(length, distance):
    """
    Mutua entre dos segmentos paralelos de igual longitud (Grover).
    M = (mu0/2pi) * length * [ ln(length/d + sqrt(1+(length/d)^2)) - sqrt(1+(d/length)^2) + d/length ]
    Devuelve valor positivo. El signo (corrientes paralelas vs antiparalelas) lo aplica el caller.
    """
    if length <= 0 or distance <= 0:
        return 0.0
    r = length / distance
    M = (MU0 / (2.0 * np.pi)) * length * (
        np.log(r + np.sqrt(1.0 + r * r)) - np.sqrt(1.0 + 1.0 / (r * r)) + 1.0 / r
    )
    return M


def greenhouse_square(d_in, w, gap, N, t):
    """
    Greenhouse 1974: espiral cuadrada como suma de segmentos rectos.
    Autoinductancias + mutuas con signo. N puede ser float (vueltas fraccionarias).
    Implementación: genera la geometría como lista de segmentos y aplica Greenhouse.
    """
    pitch = w + gap
    # Construir lista de segmentos: cada vuelta = 4 segmentos.
    # Empezamos desde el centro hacia afuera, espiral cuadrada estándar.
    # Lado interior k=0 tiene lado = d_in + w (centro de pista).
    # Para simplicidad usamos la longitud media de cada segmento.
    N_int = int(np.floor(N))
    segments = []  # cada elem: (length, direction, midpoint)
    # direction: 0=+x, 1=+y, 2=-x, 3=-y
    # midpoint: (xm, ym) coords del centro del segmento
    x, y = -d_in / 2.0, -d_in / 2.0  # esquina inferior-izq del lado interno
    side_inner = d_in
    for k in range(N_int):
        # k-ésima vuelta, lado = d_in + 2*k*pitch + w (aproximación)
        side = d_in + 2 * k * pitch
        # 4 segmentos: derecha, arriba, izquierda, abajo
        # segmento derecha (+x), mid y = -side/2 - k*pitch
        segments.append((side, 0, (0.0, -side / 2.0 - k * pitch)))
        segments.append((side, 1, (side / 2.0 + k * pitch, 0.0)))
        segments.append((side, 2, (0.0, side / 2.0 + k * pitch)))
        # último segmento de la vuelta es más corto para avanzar hacia afuera
        seg_close = side + pitch  # el "wrap-around" que crece
        segments.append((seg_close, 3, (-side / 2.0 - k * pitch, 0.0)))
    # Fracción de vuelta
    frac = N - N_int
    if frac > 0:
        side = d_in + 2 * N_int * pitch
        # añadir frac*4 segmentos parciales (aproximación gruesa)
        nseg_extra = int(frac * 4)
        for j in range(nseg_extra):
            segments.append((side, j % 4, (0.0, 0.0)))

    if not segments:
        return 0.0

    L_total = 0.0
    # autoinductancias
    for length, _, _ in segments:
        L_total += _segment_self_L(length, w, t)

    # mutuas: solo entre segmentos paralelos (misma dirección o dirección opuesta)
    n = len(segments)
    for i in range(n):
        Li, di, (xi, yi) = segments[i]
        for j in range(i + 1, n):
            Lj, dj, (xj, yj) = segments[j]
            # paralelos: direcciones iguales (cofluyentes) o opuestas (contracorriente)
            if (di % 2) != (dj % 2):
                continue
            # distancia perpendicular
            if di % 2 == 0:  # horizontal: distancia = |yi - yj|
                dist = abs(yi - yj)
                # longitud común (overlap) — aproximación: min(Li, Lj)
                Lcom = min(Li, Lj)
            else:  # vertical
                dist = abs(xi - xj)
                Lcom = min(Li, Lj)
            if dist < 1e-15:
                continue
            M = _segment_mutual_parallel(Lcom, dist)
            sign = +1 if di == dj else -1
            L_total += 2.0 * sign * M  # factor 2 porque M_ij = M_ji
    return max(L_total, 0.0)


def greenhouse_circular(d_in, w, gap, N, t, n_sides=64):
    """
    Para forma circular, aproximamos como polígono regular de n_sides por vuelta.
    Implementación simplificada: usar Mohan-Wheeler que es muy precisa para circular,
    luego refinarla con un factor de corrección Greenhouse. Aquí devolvemos Mohan
    directamente para no introducir errores numéricos (Greenhouse en circular es
    sustancialmente más complejo).
    """
    # Mantener consistencia: ofrecemos Mohan como aproximación de Greenhouse-circular
    return mohan_wheeler(d_in, w, gap, N, "circular")


def inductance_microcoil(d_in, w, gap, N, t, shape, formula):
    """Dispatcher para inductancia microcoil planar."""
    formula = formula.lower()
    shape = shape.lower()
    if formula.startswith("mohan"):
        return mohan_wheeler(d_in, w, gap, N, shape)
    elif formula.startswith("greenhouse"):
        if shape == "cuadrada":
            return greenhouse_square(d_in, w, gap, N, t)
        else:
            return greenhouse_circular(d_in, w, gap, N, t)
    else:
        return mohan_wheeler(d_in, w, gap, N, shape)


# =====================================================================
# Inductancia mutua entre anillos coaxiales (Neumann via elípticas)
# =====================================================================

def mutual_coaxial_rings(r1, r2, axial_dist=0.0):
    """
    Inductancia mutua entre dos espiras circulares coaxiales.
    Babic & Akyel 2008 / Neumann via integrales elípticas completas.
    M = mu0 * sqrt(r1*r2) * [(2/k - k)*K(k) - (2/k)*E(k)]
    k^2 = 4*r1*r2 / ((r1+r2)^2 + axial_dist^2)
    """
    if r1 <= 0 or r2 <= 0:
        return 0.0
    k2 = 4.0 * r1 * r2 / ((r1 + r2) ** 2 + axial_dist ** 2)
    k2 = min(max(k2, 0.0), 1.0 - 1e-12)
    k = np.sqrt(k2)
    K = ellipk(k2)  # scipy usa parámetro m = k^2
    E = ellipe(k2)
    M = MU0 * np.sqrt(r1 * r2) * ((2.0 / k - k) * K - (2.0 / k) * E)
    return M


def self_inductance_ring(radius, wire_radius):
    """
    Autoinductancia de un anillo circular delgado (Maxwell/Grover).
    L = mu0 * r * [ ln(8r/a) - 2 ]  donde a = radio del conductor
    """
    if radius <= 0 or wire_radius <= 0:
        return 0.0
    return MU0 * radius * (np.log(8.0 * radius / wire_radius) - 2.0)


def parallel_rings_inductance(d_in, w, gap, N, t, coupling=True):
    """
    N anillos concéntricos independientes conectados en paralelo a los mismos pads.
    Devuelve dict con 'L_total', 'L_individual', 'M_matrix'.
    Si coupling=True, usa la matriz de impedancias acopladas:
        I_total = sum I_k, V = j*omega * (L * I) (matriz)
        L_eff = V/(j*omega*I_total)
    Aproximamos por: L_eff = (sum_i sum_j L_ij) / N^2 cuando todas las espiras
    comparten voltaje y N están en paralelo (corrientes idénticas si Ls iguales).
    Para anillos en paralelo con voltaje común: I_k = V/(j*omega*L_k_eff),
    donde L_k_eff considera el flujo total = L_k + sum_{j!=k} M_kj (corrientes en
    fase y mismo sentido).
    """
    radii = []
    wire_radius = max(w, t) / 2.0  # radio equivalente del conductor
    for k in range(int(np.floor(N))):
        r_k = (d_in / 2.0) + w / 2.0 + k * (w + gap)
        radii.append(r_k)
    n = len(radii)
    if n == 0:
        return {"L_total": 0.0, "L_individual": [], "M_matrix": np.zeros((0, 0))}

    # Matriz de inductancias
    M = np.zeros((n, n))
    for i in range(n):
        M[i, i] = self_inductance_ring(radii[i], wire_radius)
        if coupling:
            for j in range(i + 1, n):
                m = mutual_coaxial_rings(radii[i], radii[j], 0.0)
                M[i, j] = m
                M[j, i] = m

    L_individual = [M[i, i] for i in range(n)]

    if coupling:
        # Asumiendo todas las corrientes en fase con mismo sentido (paralelo a mismos pads):
        # L_eff_k = sum_j M_kj  (flujo total visto por el anillo k cuando todos llevan I)
        # Las espiras están en paralelo eléctricamente, así que:
        # 1/L_total ≈ sum_k 1/L_eff_k  si los voltajes son iguales pero
        # más correctamente, resolviendo V = jw*M*I con V_k = V para todos:
        # I = (M^-1) * V * 1_vec  =>  I_total = 1^T * M^-1 * V * 1
        # L_total = V/(jw*I_total) = 1 / (1^T * M^-1 * 1)
        try:
            M_inv = np.linalg.inv(M)
            ones = np.ones(n)
            denom = ones @ M_inv @ ones
            L_total = 1.0 / denom if denom > 0 else 0.0
        except np.linalg.LinAlgError:
            L_total = 0.0
    else:
        # Sin acoplamiento: simple paralelo de Ls
        L_total = 1.0 / sum(1.0 / L for L in L_individual if L > 0)

    return {"L_total": L_total, "L_individual": L_individual, "M_matrix": M, "radii": radii}


# =====================================================================
# Inductancia — Bobinas AWG (multicapa)
# =====================================================================

def wheeler_multilayer(a_m, h_m, b_m, N):
    """
    Wheeler 1928, fórmula clásica de solenoide multicapa.
    L[μH] = 0.8 * a^2 * N^2 / (6a + 9h + 10b)   con a, h, b en pulgadas
    a = radio medio
    h = altura del bobinado (largo axial)
    b = profundidad del bobinado (radial)
    Convertir a SI:
    """
    inch = 0.0254
    a_in = a_m / inch
    h_in = h_m / inch
    b_in = b_m / inch
    denom = 6.0 * a_in + 9.0 * h_in + 10.0 * b_in
    if denom <= 0:
        return 0.0
    L_uH = 0.8 * (a_in ** 2) * (N ** 2) / denom
    return L_uH * 1e-6  # H


def pancake_multilayer(d_in, d_wire, N_per_layer, N_layers, gap_layer=0.0):
    """
    Espirales planares apiladas (pancake). Cada capa es una espiral con N_per_layer vueltas.
    Suma de autoinductancias + acoplamiento entre capas.
    Aproximación: cada capa = Mohan-Wheeler circular; mutua entre capas = mutua coaxial
    entre los anillos promedio.
    """
    # Inductancia por capa (Mohan circular). w = d_wire, gap = 0 (cables pegados radialmente)
    L_layer = mohan_wheeler(d_in, d_wire, 0.0, N_per_layer, "circular")

    # Radio medio de cada capa
    d_out = d_in + 2.0 * N_per_layer * d_wire
    r_mean = (d_in + d_out) / 4.0

    # Posiciones axiales de las capas
    layer_thickness = d_wire + gap_layer
    z_positions = [k * layer_thickness for k in range(N_layers)]

    # Inductancia total: sum de Ls + mutuas
    L_total = N_layers * L_layer
    # Acoplamiento entre capas: M efectiva = mutual_coaxial * N_per_layer^2 (aprox)
    for i in range(N_layers):
        for j in range(i + 1, N_layers):
            z_dist = abs(z_positions[i] - z_positions[j])
            M_ij = mutual_coaxial_rings(r_mean, r_mean, z_dist) * (N_per_layer ** 2)
            L_total += 2.0 * M_ij
    return L_total


# =====================================================================
# Resistencia y efecto skin
# =====================================================================

def dc_resistance(rho, length, area):
    """R_dc = rho * L / A. area en m^2."""
    if area <= 0:
        return 0.0
    return rho * length / area


def skin_depth(rho, freq, mu=MU0):
    """Profundidad de penetración por efecto skin."""
    if freq <= 0:
        return float('inf')
    return np.sqrt(rho / (np.pi * mu * freq))


def ac_resistance_rectangular(rho, length, w, t, freq):
    """
    R_ac para conductor rectangular. Si delta < min(w,t)/2, la corriente se concentra
    en una capa de espesor delta. Aproximación: R_ac = rho*L / (perimetro_efectivo * delta)
    cuando delta << w,t. Si delta es grande, R_ac ≈ R_dc.
    """
    R_dc = dc_resistance(rho, length, w * t)
    if freq <= 0:
        return R_dc
    delta = skin_depth(rho, freq)
    if delta >= min(w, t) / 2.0:
        return R_dc
    # area efectiva = perimetro * delta (anillo conductor)
    perim = 2.0 * (w + t)
    A_eff = perim * delta - 4.0 * delta * delta  # corrección esquinas
    A_eff = max(A_eff, 1e-30)
    return rho * length / A_eff


def ac_resistance_round(rho, length, wire_diameter, freq):
    """R_ac para cable cilíndrico (AWG)."""
    a = wire_diameter / 2.0
    R_dc = dc_resistance(rho, length, np.pi * a ** 2)
    if freq <= 0:
        return R_dc
    delta = skin_depth(rho, freq)
    if delta >= a:
        return R_dc
    # área anular efectiva
    A_eff = np.pi * (a ** 2 - (a - delta) ** 2)
    return rho * length / A_eff


def f_skin_threshold(rho, characteristic_dim, mu=MU0):
    """
    Frecuencia donde delta = characteristic_dim (típicamente el espesor o radio).
    Above this frequency, skin effect becomes significant.
    f = rho / (pi * mu * dim^2)
    """
    if characteristic_dim <= 0:
        return float('inf')
    return rho / (np.pi * mu * characteristic_dim ** 2)


# =====================================================================
# Factor de calidad
# =====================================================================

def quality_factor(L, R, freq):
    """Q = omega * L / R."""
    if R <= 0:
        return float('inf')
    return 2.0 * np.pi * freq * L / R


# =====================================================================
# Bibliografía
# =====================================================================

BIBLIOGRAPHY = [
    {
        "key": "Mohan1999",
        "authors": "S. S. Mohan, M. del Mar Hershenson, S. P. Boyd, T. H. Lee",
        "year": 1999,
        "title": "Simple Accurate Expressions for Planar Spiral Inductances",
        "source": "IEEE Journal of Solid-State Circuits, vol. 34, no. 10, pp. 1419–1424",
        "equation": "Inductancia microcoil planar — fórmula Wheeler modificada con K1, K2 por forma.",
    },
    {
        "key": "Greenhouse1974",
        "authors": "H. M. Greenhouse",
        "year": 1974,
        "title": "Design of Planar Rectangular Microelectronic Inductors",
        "source": "IEEE Trans. Parts, Hybrids, and Packaging, vol. 10, no. 2, pp. 101–109",
        "equation": "Método de segmentos: suma de autoinductancias y mutuas con signo.",
    },
    {
        "key": "Grover1946",
        "authors": "F. W. Grover",
        "year": 1946,
        "title": "Inductance Calculations: Working Formulas and Tables",
        "source": "Dover Publications (reimpresión 2004)",
        "equation": "Q-tablas y fórmulas de mutua para segmentos paralelos.",
    },
    {
        "key": "Wheeler1928",
        "authors": "H. A. Wheeler",
        "year": 1928,
        "title": "Simple Inductance Formulas for Radio Coils",
        "source": "Proc. IRE, vol. 16, no. 10, pp. 1398–1400",
        "equation": "Solenoide multicapa: L = 0.8·a²·N²/(6a+9h+10b) [μH, pulgadas].",
    },
    {
        "key": "Wheeler1942",
        "authors": "H. A. Wheeler",
        "year": 1942,
        "title": "Formulas for the Skin Effect",
        "source": "Proc. IRE, vol. 30, no. 9, pp. 412–424",
        "equation": "Profundidad de penetración δ = √(ρ/(π·μ·f)).",
    },
    {
        "key": "Terman1943",
        "authors": "F. E. Terman",
        "year": 1943,
        "title": "Radio Engineers' Handbook",
        "source": "McGraw-Hill, New York",
        "equation": "Tablas AWG y efecto skin en conductores redondos.",
    },
    {
        "key": "Kuhn2001",
        "authors": "W. B. Kuhn, N. M. Ibrahim",
        "year": 2001,
        "title": "Analysis of Current Crowding Effects in Multiturn Spiral Inductors",
        "source": "IEEE Trans. Microwave Theory Tech., vol. 49, no. 1, pp. 31–38",
        "equation": "Resistencia AC y crowding en espirales planares multivuelta.",
    },
    {
        "key": "Jenei2002",
        "authors": "S. Jenei, B. K. J. C. Nauwelaers, S. Decoutere",
        "year": 2002,
        "title": "Physics-Based Closed-Form Inductance Expression for Compact Modeling of Integrated Spiral Inductors",
        "source": "IEEE Journal of Solid-State Circuits, vol. 37, no. 1, pp. 77–80",
        "equation": "K1, K2 para forma circular (K1=2.46, K2=2.00).",
    },
    {
        "key": "Babic2008",
        "authors": "S. I. Babic, C. Akyel",
        "year": 2008,
        "title": "New Analytic-Numerical Solutions for the Mutual Inductance of Two Coaxial Circular Coils",
        "source": "IEEE Trans. Magnetics, vol. 44, no. 7, pp. 1894–1903",
        "equation": "Mutua entre anillos coaxiales via integrales elípticas K(k), E(k).",
    },
    {
        "key": "Yue2000",
        "authors": "C. P. Yue, S. S. Wong",
        "year": 2000,
        "title": "Physical Modelling of Spiral Inductors on Silicon",
        "source": "IEEE Trans. Electron Devices, vol. 47, no. 3, pp. 560–568",
        "equation": "Factor de calidad Q y efectos de sustrato en bobinas planares.",
    },
    {
        "key": "Thompson1999",
        "authors": "M. T. Thompson",
        "year": 1999,
        "title": "Inductance Calculation Techniques — Part I & II",
        "source": "Power Control and Intelligent Motion (PCIM), Dec. 1999",
        "equation": "Revisión práctica de fórmulas de inductancia para diseño.",
    },
    {
        "key": "ASTM-B258",
        "authors": "ASTM International",
        "year": 2018,
        "title": "Standard Specification for Standard Nominal Diameters and Cross-Sectional Areas of AWG Sizes of Solid Round Wires Used as Electrical Conductors",
        "source": "ASTM B258-18 / NEMA MW-1000",
        "equation": "Diámetro AWG: d[mm] = 0.127 · 92^((36-AWG)/39).",
    },
]


def bibliography_html(lang="en"):
    """Render bibliografía como HTML para QTextBrowser."""
    if lang == "es":
        title = "Bibliografía — Calculadoras de Bobinas"
        subtitle = "Referencias canónicas que respaldan cada ecuación implementada."
        backs = "Soporta"
    else:
        title = "Bibliography — Coil Calculators"
        subtitle = "Canonical references backing each implemented equation."
        backs = "Backs"
    parts = ['<html><body style="font-family: -apple-system, Segoe UI, Arial; font-size: 11pt; color:#2c2c2c;">']
    parts.append(f'<h2 style="color:#cc785c">{title}</h2>')
    parts.append(f'<p>{subtitle}</p>')
    parts.append('<hr>')
    for i, ref in enumerate(BIBLIOGRAPHY, 1):
        parts.append(f'<p><b>[{i}] {ref["authors"]}</b> ({ref["year"]}).<br>')
        parts.append(f'<i>"{ref["title"]}"</i>.<br>')
        parts.append(f'{ref["source"]}.<br>')
        parts.append(f'<span style="color:#6b6b6b">{backs}: {ref["equation"]}</span></p>')
    parts.append('</body></html>')
    return ''.join(parts)


# =====================================================================
# Internacionalización (toggle EN/ES)
# =====================================================================

# Diccionario inglés → español. UI default es inglés.
TRANSLATIONS_ES = {
    # Window titles
    "Microcoil Calculator — Planar Microfabricated Coils":
        "Calculadora de Microbobinas — Bobinas Planares Microfabricadas",
    "AWG Coil Calculator — Multi-layer Copper Coils":
        "Calculadora de Bobinas AWG — Bobinas de Cobre Multicapa",
    # Menu
    "File": "Archivo",
    "Export…": "Exportar…",
    "Exit": "Salir",
    "Bibliography": "Bibliografía",
    "View references": "Ver referencias",
    "Help": "Ayuda",
    "About": "Acerca de",
    "Language": "Idioma",
    "English": "Inglés",
    "Spanish": "Español",
    # Sections
    "Topology": "Topología",
    "Series (spiral)": "Serie (espiral)",
    "Parallel (rings)": "Paralelo (anillos)",
    "With mutual coupling (parallel)": "Con acoplamiento mutuo (paralelo)",
    "Shape": "Forma",
    "Square": "Cuadrada",
    "Circular": "Circular",
    "Inductance formula": "Fórmula de inductancia",
    "Method:": "Método:",
    "Conductor material": "Material conductor",
    "Preset:": "Preset:",
    "Custom": "Personalizado",
    "Geometry": "Geometría",
    "Geometry type": "Tipo de geometría",
    "Cylindrical multi-layer solenoid": "Solenoide cilíndrico multicapa",
    "Multi-layer pancake (planar)": "Pancake multicapa (planar)",
    "Winding parameters": "Parámetros de bobinado",
    "Number of turns:": "Nº de vueltas:",
    "Inner Ø:": "Ø interno:",
    "Width w:": "Ancho w:",
    "Gap:": "Gap:",
    "Thickness t:": "Espesor t:",
    "Eval. frequency:": "Frecuencia eval.:",
    "Turns/layer:": "Vueltas/capa:",
    "# Layers:": "Nº de capas:",
    "Range mode (plot)": "Modo rango (graficar)",
    "Enable range": "Activar rango",
    "Variable:": "Variable:",
    "Min:": "Mín:",
    "Max:": "Máx:",
    "Steps:": "Pasos:",
    "Unit:": "Unidad:",
    "Calculate / Redraw": "Calcular / Redibujar",
    "Results": "Resultados",
    "Coil drawing": "Dibujo de la bobina",
    "Plots (range mode)": "Gráficas (modo rango)",
    "View Bibliography": "Ver Bibliografía",
    "Close": "Cerrar",
    # Range variables
    "N turns": "N vueltas",
    "Inner diameter": "Diámetro interno",
    "Width": "Ancho",
    "Thickness": "Espesor",
    "Frequency": "Frecuencia",
    "Wire Ø": "Ø cable",
    "Turns per layer": "Vueltas por capa",
    "Number of layers": "Número de capas",
    # Results labels
    "Wire Ø (AWG": "Ø cable (AWG",
    "DC resistance": "Resistencia DC",
    "AC resistance": "Resistencia AC",
    "Quality factor": "Factor de calidad",
    "Skin-effect onset": "Inicio efecto skin",
    "Wire length": "Longitud cable",
    "Outer Ø": "Ø externo",
    "Height": "Altura",
    "Total height/thickness": "Altura/espesor total",
    "Total turns": "Vueltas totales",
    # Plot titles
    "Inductance": "Inductancia",
    # Export dialog
    "Export options": "Opciones de exportación",
    "Choose what to export. CSV requires range mode to be active.": "Elige qué exportar. CSV requiere modo rango activo.",
    "Data (CSV)": "Datos (CSV)",
    "Inductance data": "Datos de inductancia",
    "Resistance data": "Datos de resistencia",
    "Q-factor data": "Datos del factor Q",
    "Images (PNG)": "Imágenes (PNG)",
    "Inductance plot": "Gráfica inductancia",
    "Resistance plot": "Gráfica resistencia",
    "Q-factor plot": "Gráfica factor Q",
    "All three plots (combined)": "Las tres gráficas (combinadas)",
    "Output folder:": "Carpeta destino:",
    "File prefix:": "Prefijo archivo:",
    "Browse…": "Examinar…",
    "Cancel": "Cancelar",
    "Export": "Exportar",
    "Export complete": "Exportación completa",
    "Files written to:": "Archivos escritos en:",
    "No items selected.": "No se seleccionó nada.",
    "Select an output folder.": "Selecciona una carpeta de salida.",
    "Range mode is not active — no data to export.": "Modo rango no activo — no hay datos para exportar.",
    "Choose output folder": "Elegir carpeta de salida",
    # About
    "About this calculator": "Acerca de la calculadora",
    "Microcoil Calculator": "Calculadora de Microbobinas",
    "AWG Coil Calculator": "Calculadora de Bobinas AWG",
    "Inductance, resistance and quality-factor calculator\nfor planar microfabricated coils.":
        "Calculadora de inductancia, resistencia y factor de calidad\npara bobinas planares microfabricadas.",
    "Calculator for large copper coils made with AWG wire.\nSupports cylindrical multi-layer solenoids and pancake stacks.":
        "Calculadora para bobinas grandes de cobre con cable AWG.\nSoporta solenoides cilíndricos multicapa y stacks pancake.",
    "Equations: Mohan 1999, Greenhouse 1974, Babic-Akyel 2008.\nSee Bibliography menu for full references.":
        "Ecuaciones: Mohan 1999, Greenhouse 1974, Babic-Akyel 2008.\nVer menú Bibliografía para referencias completas.",
    "Equations: Wheeler 1928 (multilayer), Babic-Akyel 2008 (coupling).":
        "Ecuaciones: Wheeler 1928 (multicapa), Babic-Akyel 2008 (acoplamiento).",
}


def tr(text, lang="en"):
    """Traduce un string. Si lang='en' o no hay traducción, devuelve original."""
    if lang == "en":
        return text
    return TRANSLATIONS_ES.get(text, text)


# =====================================================================
# Hoja de estilo Qt (tema Anthropic / Claude)
# =====================================================================

STYLESHEET = """
QMainWindow, QDialog {
    background-color: #f5f1e8;
}
QFrame[panel="true"] {
    background-color: #ffffff;
    border: 1px solid #e5dccb;
    border-radius: 10px;
}
QGroupBox {
    font-family: -apple-system, "Segoe UI", Arial;
    font-weight: 600;
    font-size: 10pt;
    color: #2c2c2c;
    border: 1px solid #e5dccb;
    border-radius: 8px;
    margin-top: 14px;
    padding: 14px 8px 8px 8px;
    background-color: #fcfbf7;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    margin-left: 6px;
    color: #cc785c;
    background-color: #f5f1e8;
    font-weight: 700;
}
QLabel {
    color: #2c2c2c;
    font-family: -apple-system, "Segoe UI", Arial;
    font-size: 10pt;
}
QLabel[result="true"] {
    font-family: "Cascadia Mono", Consolas, "Courier New", monospace;
    font-size: 10pt;
    padding: 6px 8px;
    background-color: #fcfbf7;
    border: 1px solid #efe7d4;
    border-radius: 5px;
    color: #2c2c2c;
}
QLabel[header="true"] {
    font-size: 14pt;
    font-weight: 700;
    color: #cc785c;
    padding: 6px 0;
}
QLabel[caption="true"] {
    font-size: 11pt;
    font-weight: 600;
    color: #2c2c2c;
    padding: 4px 0 2px 0;
}
QPushButton {
    background-color: #cc785c;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 14px;
    font-weight: 600;
    font-size: 10pt;
    min-height: 18px;
}
QPushButton:hover { background-color: #b86547; }
QPushButton:pressed { background-color: #a05538; }
QPushButton[secondary="true"] {
    background-color: #ffffff;
    color: #2c2c2c;
    border: 1px solid #d4ccba;
}
QPushButton[secondary="true"]:hover { background-color: #f0e8d8; }
QDoubleSpinBox, QSpinBox, QComboBox, QLineEdit {
    background-color: white;
    border: 1px solid #d4ccba;
    border-radius: 5px;
    padding: 4px 6px;
    color: #2c2c2c;
    font-size: 10pt;
    min-height: 18px;
}
QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus, QLineEdit:focus {
    border-color: #cc785c;
}
QComboBox::drop-down {
    border: none;
    padding-right: 4px;
}
QRadioButton, QCheckBox {
    color: #2c2c2c;
    spacing: 8px;
    font-size: 10pt;
    padding: 2px;
}
QRadioButton::indicator, QCheckBox::indicator {
    width: 16px;
    height: 16px;
}
QMenuBar {
    background-color: #ffffff;
    color: #2c2c2c;
    border-bottom: 1px solid #e5dccb;
    font-size: 10pt;
    padding: 2px;
}
QMenuBar::item { padding: 6px 12px; background-color: transparent; }
QMenuBar::item:selected { background-color: #f0e8d8; border-radius: 4px; }
QMenu {
    background-color: white;
    border: 1px solid #e5dccb;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item { padding: 6px 18px; border-radius: 4px; }
QMenu::item:selected { background-color: #f0e8d8; }
QTextBrowser {
    background-color: #fcfbf7;
    border: 1px solid #e5dccb;
    border-radius: 8px;
    padding: 10px;
    font-size: 10pt;
}
QScrollBar:vertical {
    background: #f5f1e8;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #d4ccba;
    border-radius: 5px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover { background: #cc785c; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
"""


# Paleta para matplotlib (consistente con el tema)
PALETTE = {
    "bg_canvas":    "#ffffff",
    "bg_axes":      "#fcfbf7",
    "grid":         "#e5dccb",
    "text":         "#2c2c2c",
    "accent":       "#cc785c",
    "copper":       "#d4a358",
    "copper_dark":  "#8a6a2c",
    "copper_light": "#f0c977",
    "pad":          "#e8794a",
    "pad_edge":     "#a83a16",
    "core_hatch":   "#9c9285",
    "line_L":       "#2563eb",   # azul
    "line_R":       "#dc2626",   # rojo
    "line_Q":       "#16a34a",   # verde
}



# =====================================================================
# Utilidad: convertir valor con unidad a metros
# =====================================================================

def to_meters(value, unit):
    return value * UNITS.get(unit, 1.0)


def from_meters(value_m, unit):
    return value_m / UNITS.get(unit, 1.0)


def to_hz(value, unit):
    return value * FREQ_UNITS.get(unit, 1.0)
