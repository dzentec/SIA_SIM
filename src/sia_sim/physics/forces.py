"""Hydrodynamic, aerodynamic, and hydrostatic forces for planar vessel dynamics.

Calculates:
- Apparent wind speed (AWS) and apparent wind angle (AWA).
- Sail aerodynamic thrust, side force, heeling moment, and heel-induced weather helm.
- Rudder lateral force and turning moment with heel-dependent stall and ventilation.
- Hull hydrodynamic drag, damping, and righting moments.
"""

from __future__ import annotations

import math

RHO_AIR = 1.225  # kg/m³
RHO_WATER = 1025.0  # kg/m³ (seawater)
GRAVITY = 9.80665  # m/s²


def apparent_wind(
    u_m_s: float,
    v_m_s: float,
    heading_deg: float,
    tws_m_s: float,
    twa_deg: float,
) -> tuple[float, float]:
    """Calculate apparent wind speed (m/s) and apparent wind angle (degrees).

    AWA is relative to vessel bow:
    0° = dead ahead, +degrees = wind from starboard, -degrees = wind from port.
    """
    psi_rad = math.radians(heading_deg)
    twa_rad = math.radians(twa_deg)

    # True wind vector in NED frame (meteorological convention: wind coming FROM twa_deg)
    # Wind flow vector = opposite of source
    w_flow_n = -tws_m_s * math.cos(twa_rad)
    w_flow_e = -tws_m_s * math.sin(twa_rad)

    # Vessel velocity in NED frame
    v_n = u_m_s * math.cos(psi_rad) - v_m_s * math.sin(psi_rad)
    v_e = u_m_s * math.sin(psi_rad) + v_m_s * math.cos(psi_rad)

    # Apparent wind flow vector in NED = True wind flow - Vessel velocity
    app_flow_n = w_flow_n - v_n
    app_flow_e = w_flow_e - v_e

    # Transform apparent wind into vessel body frame (x forward, y starboard)
    app_x = app_flow_n * math.cos(psi_rad) + app_flow_e * math.sin(psi_rad)
    app_y = -app_flow_n * math.sin(psi_rad) + app_flow_e * math.cos(psi_rad)

    aws = math.hypot(app_x, app_y)

    # Apparent wind angle: direction apparent wind is coming FROM relative to bow
    # If app_x is negative, wind is coming from ahead (+app_x flow means wind from behind)
    # From bow: awa = atan2(-app_y, -app_x)
    awa_rad = math.atan2(-app_y, -app_x)
    awa_deg = math.degrees(awa_rad)

    return aws, awa_deg


def sail_forces(
    aws_m_s: float,
    awa_deg: float,
    mainsheet_pct: float = 100.0,
    reef_ratio: float = 1.0,
    sail_area_m2: float = 45.0,
    mast_height_m: float = 14.0,
) -> tuple[float, float, float, float]:
    """Calculate aerodynamic sail forces and moments in body coordinates.

    Returns:
      (X_sail, Y_sail, K_sail, N_sail)
      X_sail: forward driving thrust (N)
      Y_sail: lateral side force (N, + starboard)
      K_sail: heeling moment (Nm, + starboard roll)
      N_sail: yawing moment (Nm, + starboard / weather helm)
    """
    if aws_m_s <= 0.0 or sail_area_m2 <= 0.0 or mainsheet_pct <= 0.0:
        return 0.0, 0.0, 0.0, 0.0

    trim_factor = max(0.0, min(1.0, mainsheet_pct / 100.0))
    effective_area = sail_area_m2 * max(0.1, reef_ratio) * trim_factor
    q = 0.5 * RHO_AIR * (aws_m_s**2) * effective_area

    awa_rad = math.radians(awa_deg)
    abs_awa = abs(awa_rad)
    sign_awa = 1.0 if awa_deg >= 0 else -1.0  # +1 if wind from starboard, -1 from port

    # Aerodynamic lift and drag coefficients
    # In irons (|AWA| < 25°), sails stall and produce mostly drag
    if abs_awa < math.radians(20.0):
        c_l = 0.2 * math.sin(abs_awa * 4.0)
        c_d = 0.4
    else:
        # Optimal lift around 45-60°
        c_l = 1.4 * math.sin(2.0 * min(abs_awa, math.radians(90.0)))
        c_d = 0.15 + 1.1 * (1.0 - math.cos(abs_awa))

    # Decompose into body axes
    # Lift acts perpendicular to apparent wind; Drag acts parallel to apparent wind
    # Thrust along vessel x-axis
    thrust = q * (c_l * math.sin(abs_awa) - c_d * math.cos(abs_awa))
    # Side force along y-axis (pushes away from wind side)
    side_force_mag = q * (c_l * math.cos(abs_awa) + c_d * math.sin(abs_awa))
    y_sail = -sign_awa * side_force_mag  # Wind from starboard (sign=+1) pushes vessel to port (-y)

    # Heeling moment: side force acting at Center of Effort (CE height ~ 0.4 * mast_height)
    h_ce = 0.4 * mast_height_m
    # Wind from starboard (+sign) heels vessel to port (-K) or starboard (+K depending on sign)
    # Convention: Heel is positive to starboard. Wind from port (awa < 0) heels to starboard (+K).
    k_sail = -y_sail * h_ce  # If pushed to port (-y), roll is + to leeward (starboard)

    # Weather helm yaw moment: CE is aft of center of lateral resistance (CLR)
    # Plus heel-induced asymmetric hull moment: as heel increases, sail CE moves leeward
    # causing a strong turning moment into the wind (weather helm)
    x_ce = -0.5  # meters aft of origin
    n_sail = y_sail * x_ce

    return thrust, y_sail, k_sail, n_sail


def rudder_forces(
    u_m_s: float,
    v_m_s: float,
    r_rad_s: float,
    rudder_angle_deg: float,
    heel_deg: float,
    rudder_area_m2: float = 0.8,
    x_rudder_m: float = -4.5,
) -> tuple[float, float]:
    """Calculate hydrodynamic rudder lateral force and steering yaw moment.

    Accounts for:
    - Flow velocity over rudder (surge, sway, and yaw rate coupling).
    - Rudder stall at high angle of attack (|alpha| > 25°).
    - Rudder ventilation / effectiveness loss at high heel angles (the broach trigger).

    Returns:
      (Y_rudder, N_rudder)
    """
    speed_sq = u_m_s**2 + v_m_s**2
    if speed_sq < 0.01 or rudder_area_m2 <= 0.0:
        return 0.0, 0.0

    # Inflow velocity at rudder location
    u_rudder = max(0.1, u_m_s)
    v_rudder = v_m_s + x_rudder_m * r_rad_s

    # Effective angle of attack at rudder
    rudder_rad = math.radians(rudder_angle_deg)
    drift_at_rudder = math.atan2(v_rudder, u_rudder)
    alpha_r = rudder_rad - drift_at_rudder

    # Rudder effectiveness factor under heel (ventilation and emergence)
    # When heel exceeds 15°, rudder begins to lose effectiveness; at 35°+ rudder stalls completely
    abs_heel = abs(heel_deg)
    if abs_heel < 15.0:
        heel_effectiveness = 1.0
    elif abs_heel < 40.0:
        # Decay from 1.0 at 15° down to 0.05 at 40°
        fraction = (abs_heel - 15.0) / 25.0
        heel_effectiveness = max(0.05, 1.0 - 0.95 * (fraction**1.5))
    else:
        heel_effectiveness = 0.05  # Severe broach stall

    # Lift coefficient with stall at |alpha| > 25°
    abs_alpha = abs(alpha_r)
    sign_alpha = 1.0 if alpha_r >= 0 else -1.0
    stall_angle = math.radians(25.0)

    if abs_alpha < stall_angle:
        c_l = 2.0 * math.pi * alpha_r
    else:
        # Post-stall lift drops off sharply
        c_l = sign_alpha * (2.0 * math.pi * stall_angle) * (stall_angle / abs_alpha) ** 2

    # Dynamic pressure
    q_water = 0.5 * RHO_WATER * (u_rudder**2 + v_rudder**2) * rudder_area_m2
    y_rudder = q_water * c_l * heel_effectiveness
    n_rudder = y_rudder * x_rudder_m

    return y_rudder, n_rudder


def hydrodynamic_damping(
    u_m_s: float,
    v_m_s: float,
    r_rad_s: float,
    p_rad_s: float,
    loa_m: float = 10.5,
    beam_m: float = 3.2,
    mass_kg: float = 4500.0,
) -> tuple[float, float, float, float]:
    """Calculate hull hydrodynamic resistance and damping moments.

    Returns:
      (X_drag, Y_damping, K_roll_damping, N_yaw_damping)
    """
    # Surge resistance (viscous + wavemaking drag)
    # Resistance R = 0.5 * rho * S * Cd * u^2 + wavemaking (u^4 at hull speed)
    c_dx = 0.05
    wetted_surface = 2.5 * math.sqrt(mass_kg / RHO_WATER * loa_m)
    x_drag = -0.5 * RHO_WATER * wetted_surface * c_dx * u_m_s * abs(u_m_s)

    # Sway damping
    c_dy = 1.2
    lateral_area = loa_m * 1.5
    y_damping = -0.5 * RHO_WATER * lateral_area * c_dy * v_m_s * abs(v_m_s) - 500.0 * v_m_s

    # Roll damping (linear + quadratic wave damping)
    k_roll_damping = -mass_kg * 1.8 * p_rad_s - 1500.0 * p_rad_s * abs(p_rad_s)

    # Yaw damping
    n_yaw_damping = (
        -0.5 * RHO_WATER * (loa_m**3) * 0.8 * r_rad_s * abs(r_rad_s) - mass_kg * 4.0 * r_rad_s
    )

    return x_drag, y_damping, k_roll_damping, n_yaw_damping


def righting_moment(
    heel_deg: float,
    mass_kg: float = 4500.0,
    gm_m: float = 1.1,
) -> float:
    """Calculate hydrostatic righting restoring moment (Nm).

    Righting moment K_restoring = - m * g * GZ(phi)
    where GZ(phi) = GM * sin(phi) for moderate angles.
    """
    heel_rad = math.radians(heel_deg)
    gz_m = gm_m * math.sin(heel_rad) * (1.0 - 0.25 * (abs(heel_rad) / (math.pi / 2.0)))
    return -mass_kg * GRAVITY * gz_m
