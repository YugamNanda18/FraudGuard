"""Codigos de materia y departamento del BOE relevantes para fraude bancario.

Fuente: https://www.boe.es/datosabiertos/api/datos-auxiliares/
Fecha de mapeo: 2026-04-06

Obtenido via curl a los endpoints:
  - GET /datos-auxiliares/materias  (Accept: application/json)
  - GET /datos-auxiliares/departamentos  (Accept: application/json)

Criterio de seleccion: materias y departamentos directamente relacionados con
fraude bancario, prevencion de blanqueo de capitales, sistema financiero,
derecho penal economico, proteccion de datos, ciberseguridad y regulacion
financiera.
"""

# ---------------------------------------------------------------------------
# Materias relevantes para el dominio de fraude bancario
# Formato: {codigo: descripcion}
# ---------------------------------------------------------------------------

# --- Blanqueo de capitales y prevencion ---
MATERIAS_BLANQUEO: dict[str, str] = {
    "1071": "Comision de Prevencion del Blanqueo de Capitales e Infracciones Monetarias",
    "1383": "Consejo Asesor de Lucha contra el Trafico de Drogas y Blanqueo de Capitales",
    "1570": "Consejo Superior de Lucha contra el Trafico de Drogas y Blanqueo de Capitales",
    "8018": "Comision de Vigilancia de Actividades de Financiacion del Terrorismo",
    "2407": "Delitos monetarios",
    "4708": "Juzgado de Delitos Monetarios",
    "1081": "Comision de Vigilancia de las Infracciones de Control de Cambios",
    "1674": "Control de cambios",
}

# --- Fraude y delitos economicos ---
MATERIAS_FRAUDE_DELITOS: dict[str, str] = {
    "3822": "Fraudes",
    "3821": "Fraude de Ley",
    "5222": "Oficina Europea de Lucha contra el Fraude",
    "2348": "Delitos contra el orden socioeconomico",
    "8055": "Delitos contra el patrimonio y contra el orden socioeconomico",
    "2349": "Delitos contra el patrimonio",
    "2396": "Delitos contra la corrupcion en las transacciones comerciales internacionales",
    "2398": "Delitos de falsedad",
    "3586": "Falsedades",
    "2406": "Delitos informaticos",
    "8064": "Delitos relativos al mercado y a los consumidores",
    "2353": "Delitos contra la Administracion Publica",
    "2360": "Delitos contra la Hacienda Publica",
    "2381": "Delitos contra la Seguridad Social",
    "2401": "Delitos de los Funcionarios Publicos en el ejercicio de sus cargos",
    "2370": "Delitos contra la propiedad",
    "1638": "Contrabando",
    "6973": "Tribunal Superior de Contrabando",
    "9130": "Delitos de pirateria",
}

# --- Derecho penal ---
MATERIAS_PENAL: dict[str, str] = {
    "886": "Codigo Penal",
    "887": "Codigo Penal Militar",
    "238": "Antecedentes penales",
    "3199": "Enjuiciamiento Criminal",
    "4565": "Juicio Penal Abreviado",
    "1746": "Corte Penal Internacional",
    "4712": "Juzgados Centrales de lo Penal",
    "4717": "Juzgados de lo Penal",
    "6949": "Tribunal Central de lo Penal",
    "1193": "Comision Nacional para la Prevencion del Delito",
    "2339": "Delitos",
    "5951": "Registro Central de Sanciones",
    "6273": "Sanciones",
    "4171": "Infracciones",
}

# --- Banca y entidades de credito ---
MATERIAS_BANCA: dict[str, str] = {
    "438": "Banca",
    "449": "Banco de Espana",
    "441": "Banco Central Europeo",
    "337": "Asociacion Espanola de Banca Privada",
    "1538": "Consejo Superior Bancario",
    "1733": "Corporacion Bancaria de Espana",
    "5256": "Ordenacion bancaria",
    "3233": "Entidades de credito",
    "3445": "Establecimientos financieros de credito",
    "563": "Cajas de Ahorro",
    "1340": "Confederacion Espanola de Cajas de Ahorro",
    "1712": "Cooperativas de credito",
    "350": "Asociacion Nacional de Entidades de Financiacion",
    "578": "Camaras de Compensacion Bancaria",
    "1304": "Compensacion Bancaria",
    "6564": "Servicio de Liquidacion del Banco de Espana",
    "8016": "Servicio Espanol de Pagos Interbancarios",
    "1225": "Comisionado para la Defensa del Cliente de Servicios Bancarios",
    "3752": "Fondo de Garantia de Depositos",
    "6923": "Transferencias bancarias",
}

# --- Sistema financiero ---
MATERIAS_SISTEMA_FINANCIERO: dict[str, str] = {
    "7896": "Sistema financiero",
    "60": "Activos financieros",
    "302": "Arrendamiento Financiero",
    "3171": "Empresas de arrendamiento financiero",
    "3532": "Factoring",
    "5680": "Prestamos",
    "5681": "Prestamos mercantiles",
    "2429": "Depositos",
    "560": "Caja General de Depositos",
    "831": "Cheques",
    "4762": "Letra de cambio",
    "4775": "Libranzas vales y pagares",
    "5341": "Pagares",
    "4777": "Libre circulacion de capitales",
    "1627": "Contabilidad",
    "385": "Auditoria de Cuentas",
    "4319": "Instituto de Contabilidad y Auditoria de Cuentas",
}

# --- Mercado de valores e inversiones ---
MATERIAS_MERCADO_VALORES: dict[str, str] = {
    "4930": "Mercado de Valores",
    "1186": "Comision Nacional del Mercado de Valores",
    "1418": "Consejo de la Comision Nacional del Mercado de Valores",
    "8147": "Autoridad Europea de Valores y Mercados",
    "521": "Bolsas de Valores",
    "520": "Bolsas de Comercio",
    "149": "Agentes de Cambio y Bolsa",
    "932": "Colegios de Agentes de Cambio y Bolsa",
    "140": "Agencias de valores",
    "1665": "Contratos de futuros y opciones",
    "4933": "Mercados de Futuros y Opciones",
    "5738": "Productos financieros derivados",
    "4302": "Instituciones de Inversion Colectiva",
    "6697": "Sociedades Gestoras de Instituciones de Inversion Colectiva",
    "3789": "Fondos de Capital Riesgo",
    "6682": "Sociedades de Capital Riesgo",
    "3796": "Fondos de Titulizacion de Activos",
    "3797": "Fondos de Titulizacion Hipotecaria",
    "8082": "Sociedades Gestoras de Fondos de Titulizacion de Activos",
    "677": "Cedulas para inversiones",
}

# --- Seguros ---
MATERIAS_SEGUROS: dict[str, str] = {
    "6521": "Seguros",
    "8040": "Contrato de seguro",
    "2947": "Direccion General de Seguros",
    "2948": "Direccion General de Seguros y Fondos de Pensiones",
    "1612": "Consorcio de Compensacion de Seguros",
    "6506": "Seguro de credito",
    "6505": "Seguro de caucion",
    "6512": "Seguro de responsabilidad civil",
    "152": "Agentes de Seguros",
    "1738": "Corredores de seguros",
    "937": "Colegios de Mediadores de Seguros Titulados",
    "64": "Actuarios de seguros",
    "1716": "Cooperativas de seguros",
    "4109": "Impuesto sobre las Primas de Seguros",
    "6947": "Tribunal Arbitral de Seguros",
    "7000": "Union Espanola de Entidades Aseguradoras y Reaseguros",
}

# --- Servicios de pago y dinero electronico ---
MATERIAS_PAGOS: dict[str, str] = {
    "2503": "Dinero electronico",
    "3234": "Entidades de Dinero Electronico",
    "3443": "Establecimientos de cambio de moneda",
    "5036": "Moneda",
    "5037": "Moneda extranjera",
    "3495": "Euro",
    "3530": "Fabrica Nacional de Moneda y Timbre",
    "3531": "Fabrica Nacional de Moneda y Timbre Real Casa de la Moneda",
    "5232": "Oficinas de cambio de divisas",
    "3072": "Divisas",
    "1775": "Cuentas en divisas de residentes",
    "6655": "Sistema Monetario Europeo",
    "4373": "Instituto Espanol de Moneda Extranjera",
    "4394": "Instituto Monetario Europeo",
    "430": "Balanza de Pagos",
}

# --- Proteccion de datos ---
MATERIAS_PROTECCION_DATOS: dict[str, str] = {
    "113": "Agencia de Proteccion de Datos",
    "7908": "Agencia Espanola de Proteccion de Datos",
    "6809": "Supervisor Europeo de Proteccion de Datos",
    "6000": "Registro General de Proteccion de Datos",
    "3685": "Ficheros con datos personales",
    "35": "Acceso a la informacion",
}

# --- Tecnologia, digital e inteligencia artificial ---
MATERIAS_TECNOLOGIA: dict[str, str] = {
    "3854": "Inteligencia artificial",
    "4665": "Direccion General de Digitalizacion e Inteligencia Artificial",
    "9645": "Secretaria de Estado de Digitalizacion e Inteligencia Artificial",
    "344": "Secretaria General de Administracion Digital",
    "1001": "Comercio electronico",
    "3716": "Firma electronica",
    "4189": "Seguridad informatica",
    "2406": "Delitos informaticos",
    "473": "Bases de datos",
    "6854": "Telecomunicaciones",
    "9646": "Secretaria de Estado de Telecomunicaciones e Infraestructuras Digitales",
    "2980": "Direccion General de Telecomunicaciones",
    "2981": "Direccion General de Telecomunicaciones y Tecnologias de la Informacion",
    "1239": "Comisiones de Tecnologias de la Informacion y de las Telecomunicaciones",
    "2224": (
        "Cuerpo Superior de Sistemas y Tecnologias"
        " de la Informacion de la Administracion del Estado"
    ),
}

# --- Consumidores y usuarios (contexto financiero) ---
MATERIAS_CONSUMIDORES: dict[str, str] = {
    "1624": "Consumidores y usuarios",
    "1401": "Consejo de Consumidores y Usuarios",
    "1423": "Consejo de los Consumidores",
    "357": "Asociaciones de consumidores",
    "1710": "Cooperativas de consumidores y usuarios",
    "1258": "Comision Nacional de los Mercados y la Competencia",
    "2760": "Direccion General de los Consumidores",
    "2898": "Direccion General de Proteccion de los Consumidores",
    "8064": "Delitos relativos al mercado y a los consumidores",
}

# --- Terrorismo (financiacion) ---
MATERIAS_TERRORISMO: dict[str, str] = {
    "6875": "Terrorismo",
    "8018": "Comision de Vigilancia de Actividades de Financiacion del Terrorismo",
    "2946": "Direccion General de Seguridad Desarme y Asuntos Internacionales de Terrorismo",
}

# --- Transparencia y gobierno ---
MATERIAS_TRANSPARENCIA: dict[str, str] = {
    "6924": "Transparencia fiscal",
    "6925": "Transparencia fiscal internacional",
}

# --- Procedimientos concursales (insolvencia) ---
MATERIAS_CONCURSAL: dict[str, str] = {
    "8020": "Administracion concursal",
    "8021": "Procedimiento concursal",
    "5808": "Quiebra",
    "6813": "Suspension de pagos",
}

# ---------------------------------------------------------------------------
# Agregado: todas las materias relevantes en un unico diccionario
# ---------------------------------------------------------------------------
MATERIAS_FRAUDE: dict[str, str] = {
    # Blanqueo de capitales y prevencion
    "1071": "Comision de Prevencion del Blanqueo de Capitales e Infracciones Monetarias",
    "1383": "Consejo Asesor de Lucha contra el Trafico de Drogas y Blanqueo de Capitales",
    "1570": "Consejo Superior de Lucha contra el Trafico de Drogas y Blanqueo de Capitales",
    "8018": "Comision de Vigilancia de Actividades de Financiacion del Terrorismo",
    "2407": "Delitos monetarios",
    "4708": "Juzgado de Delitos Monetarios",
    "1081": "Comision de Vigilancia de las Infracciones de Control de Cambios",
    "1674": "Control de cambios",
    # Fraude y delitos economicos
    "3822": "Fraudes",
    "3821": "Fraude de Ley",
    "5222": "Oficina Europea de Lucha contra el Fraude",
    "2348": "Delitos contra el orden socioeconomico",
    "8055": "Delitos contra el patrimonio y contra el orden socioeconomico",
    "2349": "Delitos contra el patrimonio",
    "2396": "Delitos contra la corrupcion en las transacciones comerciales internacionales",
    "2398": "Delitos de falsedad",
    "3586": "Falsedades",
    "2406": "Delitos informaticos",
    "8064": "Delitos relativos al mercado y a los consumidores",
    "2353": "Delitos contra la Administracion Publica",
    "2360": "Delitos contra la Hacienda Publica",
    "2381": "Delitos contra la Seguridad Social",
    "2401": "Delitos de los Funcionarios Publicos en el ejercicio de sus cargos",
    "2370": "Delitos contra la propiedad",
    "1638": "Contrabando",
    # Derecho penal
    "886": "Codigo Penal",
    "3199": "Enjuiciamiento Criminal",
    "4565": "Juicio Penal Abreviado",
    "2339": "Delitos",
    "5951": "Registro Central de Sanciones",
    "6273": "Sanciones",
    "4171": "Infracciones",
    # Banca y entidades de credito
    "438": "Banca",
    "449": "Banco de Espana",
    "441": "Banco Central Europeo",
    "5256": "Ordenacion bancaria",
    "3233": "Entidades de credito",
    "3445": "Establecimientos financieros de credito",
    "563": "Cajas de Ahorro",
    "1712": "Cooperativas de credito",
    "578": "Camaras de Compensacion Bancaria",
    "1304": "Compensacion Bancaria",
    "6564": "Servicio de Liquidacion del Banco de Espana",
    "8016": "Servicio Espanol de Pagos Interbancarios",
    "1225": "Comisionado para la Defensa del Cliente de Servicios Bancarios",
    "3752": "Fondo de Garantia de Depositos",
    "6923": "Transferencias bancarias",
    # Sistema financiero
    "7896": "Sistema financiero",
    "60": "Activos financieros",
    "302": "Arrendamiento Financiero",
    "3532": "Factoring",
    "5680": "Prestamos",
    "831": "Cheques",
    "4762": "Letra de cambio",
    "5341": "Pagares",
    "4777": "Libre circulacion de capitales",
    "1627": "Contabilidad",
    "385": "Auditoria de Cuentas",
    "4319": "Instituto de Contabilidad y Auditoria de Cuentas",
    # Mercado de valores
    "4930": "Mercado de Valores",
    "1186": "Comision Nacional del Mercado de Valores",
    "8147": "Autoridad Europea de Valores y Mercados",
    "521": "Bolsas de Valores",
    "140": "Agencias de valores",
    "1665": "Contratos de futuros y opciones",
    "5738": "Productos financieros derivados",
    "4302": "Instituciones de Inversion Colectiva",
    "3796": "Fondos de Titulizacion de Activos",
    # Seguros
    "6521": "Seguros",
    "8040": "Contrato de seguro",
    "2948": "Direccion General de Seguros y Fondos de Pensiones",
    "1612": "Consorcio de Compensacion de Seguros",
    "6506": "Seguro de credito",
    "6505": "Seguro de caucion",
    # Servicios de pago y dinero electronico
    "2503": "Dinero electronico",
    "3234": "Entidades de Dinero Electronico",
    "3443": "Establecimientos de cambio de moneda",
    "5036": "Moneda",
    "3495": "Euro",
    "3072": "Divisas",
    "6655": "Sistema Monetario Europeo",
    "430": "Balanza de Pagos",
    # Proteccion de datos
    "113": "Agencia de Proteccion de Datos",
    "7908": "Agencia Espanola de Proteccion de Datos",
    "6809": "Supervisor Europeo de Proteccion de Datos",
    "6000": "Registro General de Proteccion de Datos",
    "3685": "Ficheros con datos personales",
    "35": "Acceso a la informacion",
    # Tecnologia, digital e IA
    "3854": "Inteligencia artificial",
    "4665": "Direccion General de Digitalizacion e Inteligencia Artificial",
    "9645": "Secretaria de Estado de Digitalizacion e Inteligencia Artificial",
    "344": "Secretaria General de Administracion Digital",
    "1001": "Comercio electronico",
    "3716": "Firma electronica",
    "4189": "Seguridad informatica",
    "473": "Bases de datos",
    "6854": "Telecomunicaciones",
    # Consumidores y usuarios
    "1624": "Consumidores y usuarios",
    "1401": "Consejo de Consumidores y Usuarios",
    "357": "Asociaciones de consumidores",
    "1258": "Comision Nacional de los Mercados y la Competencia",
    # Terrorismo (financiacion)
    "6875": "Terrorismo",
    # Transparencia
    "6924": "Transparencia fiscal",
    "6925": "Transparencia fiscal internacional",
    # Procedimientos concursales
    "8020": "Administracion concursal",
    "8021": "Procedimiento concursal",
    "5808": "Quiebra",
    "6813": "Suspension de pagos",
}

# ---------------------------------------------------------------------------
# Departamentos relevantes
# Fuente: GET /datos-auxiliares/departamentos
# ---------------------------------------------------------------------------
DEPARTAMENTOS_RELEVANTES: dict[str, str] = {
    # Economia y Hacienda (denominaciones historicas y actuales)
    "5110": "Ministerio de Economia",
    "9589": "Ministerio de Economia, Comercio y Empresa",
    "9576": "Ministerio de Asuntos Economicos y Transformacion Digital",
    "9281": "Ministerio de Economia, Industria y Competitividad",
    "9221": "Ministerio de Economia y Competitividad",
    "9567": "Ministerio de Economia y Empresa",
    "5130": "Ministerio de Economia y Hacienda",
    "5140": "Ministerio de Hacienda",
    "9279": "Ministerio de Hacienda y Funcion Publica",
    "4568": "Ministerio de Hacienda y Funcion Publica",
    "9350": "Ministerio de Hacienda y Administraciones Publicas",
    # Transformacion Digital
    "9594": "Ministerio de Transformacion Digital",
    "9595": "Ministerio para la Transformacion Digital y de la Funcion Publica",
    # Interior y Justicia
    "7320": "Ministerio del Interior",
    "4810": "Ministerio de Justicia",
    "9585": "Ministerio de la Presidencia, Justicia y Relaciones con las Cortes",
    # Presidencia
    "7710": "Ministerio de la Presidencia",
    "7786": "Presidencia del Gobierno",
    "7723": "Jefatura del Estado",
    # Reguladores y supervisores
    "1020": "Banco de Espana",
    "1040": "Comision Nacional del Mercado de Valores",
    "9534": "Comision Nacional de los Mercados y la Competencia",
    "1012": "Agencia de Proteccion de Datos",
    "1011": "Agencia Espanola de Proteccion de Datos",
    "9533": "Fondo de Reestructuracion Ordenada Bancaria",
    # Organos jurisdiccionales y constitucionales
    "1410": "Tribunal Constitucional",
    "1420": "Tribunal de Cuentas",
    "1430": "Tribunal Supremo",
    "1220": "Cortes Generales",
    "4510": "Ministerio Fiscal",
    "4809": "Fiscalia Europea",
    # Consumo
    "9578": "Ministerio de Consumo",
    "9588": "Ministerio de Derechos Sociales, Consumo y Agenda 2030",
    # Ciencia e innovacion
    "4245": "Ministerio de Ciencia e Innovacion",
    "9565": "Ministerio de Ciencia, Innovacion y Universidades",
}

# ---------------------------------------------------------------------------
# Rangos normativos a priorizar en las busquedas
# ---------------------------------------------------------------------------
RANGOS_PRIORITARIOS: list[str] = [
    "Ley",
    "Ley Organica",
    "Real Decreto-ley",
    "Real Decreto",
    "Real Decreto Legislativo",
    "Orden",
    "Circular",
    "Directiva",
    "Reglamento",
    "Resolucion",
    "Instruccion",
    "Acuerdo",
]

# ---------------------------------------------------------------------------
# Conjuntos de codigos para busquedas rapidas (solo codigos, sin descripcion)
# ---------------------------------------------------------------------------
CODIGOS_MATERIAS: frozenset[str] = frozenset(MATERIAS_FRAUDE.keys())
CODIGOS_DEPARTAMENTOS: frozenset[str] = frozenset(DEPARTAMENTOS_RELEVANTES.keys())
