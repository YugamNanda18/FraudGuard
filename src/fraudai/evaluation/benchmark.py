"""Benchmark dataset of 50 questions on Spanish financial fraud regulation.

Each question targets real normativa espanola / europea and includes:
    - Specific article references in ground_truth
    - expected_contexts for automated context precision / recall evaluation
    - Category tags: aml, psd2, penal, rgpd, ai_act

Sources verified against:
    - Ley 10/2010 de prevencion del blanqueo de capitales
    - Real Decreto 304/2014 (Reglamento Ley 10/2010)
    - Ley Organica 10/1995 (Codigo Penal)
    - Reglamento (UE) 2015/847 (Transferencias de fondos)
    - Directiva (UE) 2015/2366 (PSD2)
    - Real Decreto-ley 19/2018 de servicios de pago
    - Reglamento (UE) 2016/679 (RGPD)
    - Ley Organica 3/2018 (LOPDGDD)
    - Reglamento (UE) 2024/1689 (AI Act)
"""

from __future__ import annotations

from fraudai.evaluation.ragas_eval import BenchmarkQuestion

# ---------------------------------------------------------------------------
# AML / Blanqueo de capitales (10 preguntas)
# ---------------------------------------------------------------------------

_AML_QUESTIONS: list[BenchmarkQuestion] = [
    BenchmarkQuestion(
        question="Cual es el umbral de identificacion de clientes segun la Ley 10/2010?",
        ground_truth=(
            "El articulo 3.1 de la Ley 10/2010 establece la obligacion de identificar "
            "a los intervinientes cuando se establezca una relacion de negocios o se "
            "realicen operaciones por importe igual o superior a 1.000 euros, ya sea "
            "en una sola operacion o en varias que parezcan estar vinculadas."
        ),
        expected_contexts=["Ley 10/2010", "Art. 3"],
        category="aml",
        difficulty="easy",
    ),
    BenchmarkQuestion(
        question="Quienes son sujetos obligados segun la Ley 10/2010 de prevencion del blanqueo?",
        ground_truth=(
            "El articulo 2 de la Ley 10/2010 enumera los sujetos obligados, incluyendo "
            "entidades de credito, entidades aseguradoras autorizadas en el ramo de vida, "
            "empresas de servicios de inversion, sociedades gestoras de instituciones de "
            "inversion colectiva, entidades de pago, entidades de dinero electronico, "
            "promotores inmobiliarios, auditores de cuentas, notarios, registradores, "
            "abogados y procuradores (cuando participen en operaciones financieras), "
            "entre otros."
        ),
        expected_contexts=["Ley 10/2010", "Art. 2"],
        category="aml",
        difficulty="easy",
    ),
    BenchmarkQuestion(
        question="Cuando debe aplicarse diligencia debida reforzada segun la Ley 10/2010?",
        ground_truth=(
            "El articulo 11 de la Ley 10/2010 establece que debe aplicarse diligencia "
            "debida reforzada en situaciones de mayor riesgo, incluyendo: relaciones "
            "de negocio y operaciones no presenciales, corresponsalia bancaria "
            "transfronteriza, operaciones con personas con responsabilidad publica (PEP), "
            "y productos u operaciones propicios al anonimato o con nuevas tecnologias."
        ),
        expected_contexts=["Ley 10/2010", "Art. 11"],
        category="aml",
        difficulty="medium",
    ),
    BenchmarkQuestion(
        question=(
            "Cual es la obligacion de comunicacion de operaciones sospechosas "
            "al SEPBLAC segun la Ley 10/2010?"
        ),
        ground_truth=(
            "El articulo 18 de la Ley 10/2010 obliga a los sujetos obligados a "
            "comunicar por iniciativa propia al Servicio Ejecutivo de la Comision "
            "(SEPBLAC) cualquier hecho u operacion respecto al que exista indicio "
            "o certeza de que esta relacionado con el blanqueo de capitales o la "
            "financiacion del terrorismo, incluso en grado de tentativa."
        ),
        expected_contexts=["Ley 10/2010", "Art. 18"],
        category="aml",
        difficulty="easy",
    ),
    BenchmarkQuestion(
        question=("Que requisitos debe cumplir el organo de control interno segun la Ley 10/2010?"),
        ground_truth=(
            "El articulo 26 de la Ley 10/2010 exige a los sujetos obligados establecer "
            "un organo de control interno responsable de la aplicacion de las politicas "
            "y procedimientos de prevencion. El representante ante el SEPBLAC debe tener "
            "rango de administrador o directivo, y el organo de control interno debe "
            "contar con los recursos humanos, materiales y tecnicos necesarios."
        ),
        expected_contexts=["Ley 10/2010", "Art. 26"],
        category="aml",
        difficulty="medium",
    ),
    BenchmarkQuestion(
        question="Que es el examen especial regulado en la Ley 10/2010?",
        ground_truth=(
            "El articulo 17 de la Ley 10/2010 establece que los sujetos obligados "
            "deberan examinar con especial atencion cualquier hecho u operacion, con "
            "independencia de su cuantia, que por su naturaleza pueda estar relacionado "
            "con el blanqueo de capitales o la financiacion del terrorismo. Este examen "
            "especial debe quedar documentado por escrito."
        ),
        expected_contexts=["Ley 10/2010", "Art. 17"],
        category="aml",
        difficulty="medium",
    ),
    BenchmarkQuestion(
        question="Que operaciones deben comunicarse sistematicamente al SEPBLAC?",
        ground_truth=(
            "El articulo 20 de la Ley 10/2010 establece la obligacion de comunicacion "
            "sistematica, incluyendo operaciones que superen los umbrales establecidos "
            "reglamentariamente. El Real Decreto 304/2014, en su articulo 27, fija "
            "estos umbrales, incluyendo movimientos de medio de pago al portador por "
            "importe igual o superior a 30.000 euros en operaciones transfronterizas "
            "y 100.000 euros en operaciones nacionales."
        ),
        expected_contexts=["Ley 10/2010", "Art. 20", "Real Decreto 304/2014"],
        category="aml",
        difficulty="hard",
    ),
    BenchmarkQuestion(
        question=("Cuales son las sanciones por incumplimiento grave de la Ley 10/2010?"),
        ground_truth=(
            "El articulo 52 de la Ley 10/2010 tipifica las infracciones graves, "
            "y el articulo 57 establece sanciones que incluyen: multa cuyo importe "
            "minimo sera de 60.001 euros y cuyo importe maximo podra ascender hasta "
            "la mayor de las siguientes cifras: el 1% del patrimonio neto del sujeto "
            "obligado, el tanto del contenido economico de la operacion, mas un 50%, "
            "o 150.000 euros. Tambien puede conllevar amonestacion publica."
        ),
        expected_contexts=["Ley 10/2010", "Art. 52", "Art. 57"],
        category="aml",
        difficulty="hard",
    ),
    BenchmarkQuestion(
        question=("Que medidas de diligencia debida simplificada permite la Ley 10/2010?"),
        ground_truth=(
            "El articulo 9 de la Ley 10/2010 permite la aplicacion de medidas "
            "simplificadas de diligencia debida cuando se aprecie que el riesgo de "
            "blanqueo de capitales o financiacion del terrorismo es reducido, atendiendo "
            "al tipo de cliente, al producto, servicio u operacion, y al area geografica. "
            "El Real Decreto 304/2014, articulos 15 a 17, desarrolla los supuestos "
            "concretos de aplicacion."
        ),
        expected_contexts=["Ley 10/2010", "Art. 9"],
        category="aml",
        difficulty="medium",
    ),
    BenchmarkQuestion(
        question=("Que obligacion de conservacion de documentos establece la Ley 10/2010?"),
        ground_truth=(
            "El articulo 25 de la Ley 10/2010 establece que los sujetos obligados "
            "conservaran durante un periodo minimo de diez anios la documentacion en "
            "que se formalice el cumplimiento de las obligaciones de la ley, incluyendo "
            "copias de los documentos de identificacion, los documentos exigidos en la "
            "diligencia debida, y los documentos acreditativos de las operaciones "
            "(originales o copias con fuerza probatoria)."
        ),
        expected_contexts=["Ley 10/2010", "Art. 25"],
        category="aml",
        difficulty="easy",
    ),
]

# ---------------------------------------------------------------------------
# PSD2 / Servicios de pago (10 preguntas)
# ---------------------------------------------------------------------------

_PSD2_QUESTIONS: list[BenchmarkQuestion] = [
    BenchmarkQuestion(
        question="Que es la autenticacion reforzada de clientes (SCA) segun la PSD2?",
        ground_truth=(
            "El articulo 98 de la Directiva (UE) 2015/2366 (PSD2) y el articulo 68 "
            "del Real Decreto-ley 19/2018 de servicios de pago establecen la obligacion "
            "de aplicar autenticacion reforzada (SCA), que requiere al menos dos de tres "
            "elementos: algo que el cliente posee (token, movil), algo que el cliente "
            "sabe (PIN, contrasena), y algo que el cliente es (biometria)."
        ),
        expected_contexts=["PSD2", "Real Decreto-ley 19/2018", "Art. 68"],
        category="psd2",
        difficulty="easy",
    ),
    BenchmarkQuestion(
        question="Que son los proveedores de servicios de iniciacion de pagos (PISP)?",
        ground_truth=(
            "Los PISP estan regulados en el articulo 4.15 de la Directiva PSD2 "
            "(2015/2366) y en el articulo 3 del Real Decreto-ley 19/2018. Son entidades "
            "que inician una orden de pago a peticion del usuario con cargo a una cuenta "
            "de pago mantenida en otro proveedor de servicios de pago, proporcionando "
            "un servicio de iniciacion de pagos como intermediario."
        ),
        expected_contexts=["PSD2", "Real Decreto-ley 19/2018"],
        category="psd2",
        difficulty="medium",
    ),
    BenchmarkQuestion(
        question="Que son los servicios de informacion sobre cuentas (AISP) en la PSD2?",
        ground_truth=(
            "Los proveedores de servicios de informacion sobre cuentas (AISP) estan "
            "regulados en el articulo 4.16 de la Directiva PSD2 y en el articulo 3 "
            "del Real Decreto-ley 19/2018. Son entidades que proporcionan informacion "
            "agregada sobre una o varias cuentas de pago del usuario mantenidas en "
            "uno o varios proveedores de servicios de pago, ofreciendo una vision "
            "consolidada de la situacion financiera del usuario."
        ),
        expected_contexts=["PSD2", "Real Decreto-ley 19/2018"],
        category="psd2",
        difficulty="medium",
    ),
    BenchmarkQuestion(
        question="Que excepciones existen a la autenticacion reforzada (SCA)?",
        ground_truth=(
            "El Reglamento Delegado (UE) 2018/389 complementa la PSD2 estableciendo "
            "excepciones a la SCA, incluyendo: pagos contactless de bajo importe "
            "(hasta 50 EUR, acumulado maximo 150 EUR), transferencias recurrentes "
            "al mismo beneficiario, operaciones de bajo riesgo basadas en el analisis "
            "de riesgo de la transaccion (TRA) con tasas de fraude por debajo de "
            "umbrales definidos, y pagos a beneficiarios de confianza."
        ),
        expected_contexts=["PSD2", "Reglamento Delegado 2018/389"],
        category="psd2",
        difficulty="hard",
    ),
    BenchmarkQuestion(
        question=(
            "Que responsabilidad tiene el proveedor de servicios de pago "
            "ante operaciones no autorizadas?"
        ),
        ground_truth=(
            "Los articulos 44 y 45 del Real Decreto-ley 19/2018 establecen que el "
            "proveedor de servicios de pago del ordenante sera responsable de devolver "
            "de inmediato el importe de la operacion no autorizada, salvo que tenga "
            "motivos razonables para sospechar fraude del usuario. El usuario soportara "
            "como maximo 50 EUR de perdidas derivadas de operaciones no autorizadas "
            "por uso de instrumento extraviado o sustraido, excepto en casos de "
            "negligencia grave o fraude."
        ),
        expected_contexts=["Real Decreto-ley 19/2018", "Art. 44", "Art. 45"],
        category="psd2",
        difficulty="medium",
    ),
    BenchmarkQuestion(
        question="Que obligaciones de seguridad impone la PSD2 a los proveedores de pago?",
        ground_truth=(
            "El articulo 69 del Real Decreto-ley 19/2018, transpondo el articulo 95 "
            "de la PSD2, exige a los proveedores de servicios de pago establecer un "
            "marco de gestion de riesgos operativos y de seguridad, incluyendo: medidas "
            "de seguridad adecuadas para proteger la confidencialidad e integridad de "
            "los datos, mecanismos de autenticacion reforzada, y notificacion al Banco "
            "de Espana de incidentes operativos o de seguridad graves."
        ),
        expected_contexts=["Real Decreto-ley 19/2018", "Art. 69", "PSD2"],
        category="psd2",
        difficulty="medium",
    ),
    BenchmarkQuestion(
        question="Que requisitos de registro deben cumplir las entidades de pago en Espana?",
        ground_truth=(
            "Los articulos 11 a 14 del Real Decreto-ley 19/2018 establecen que las "
            "entidades de pago deben obtener autorizacion del Ministerio de Asuntos "
            "Economicos e inscribirse en el Registro Especial del Banco de Espana. "
            "Los requisitos incluyen un capital inicial minimo (entre 20.000 y 125.000 "
            "euros segun los servicios), plan de actividades, estructura organizativa "
            "adecuada, y mecanismos de control interno."
        ),
        expected_contexts=["Real Decreto-ley 19/2018", "Art. 11"],
        category="psd2",
        difficulty="hard",
    ),
    BenchmarkQuestion(
        question=("Como se regula el acceso a las cuentas de pago por terceros proveedores?"),
        ground_truth=(
            "El articulo 30 del Real Decreto-ley 19/2018 regula el acceso a cuentas "
            "de pago por parte de PISP y AISP. Los proveedores de servicios de pago "
            "gestores de cuentas deben permitir el acceso a traves de interfaces "
            "dedicadas seguras (APIs). El acceso esta sujeto al consentimiento "
            "explicito del titular de la cuenta y a la autenticacion reforzada."
        ),
        expected_contexts=["Real Decreto-ley 19/2018", "Art. 30"],
        category="psd2",
        difficulty="medium",
    ),
    BenchmarkQuestion(
        question="Que plazo tiene el proveedor de pagos para resolver reclamaciones?",
        ground_truth=(
            "El articulo 48 del Real Decreto-ley 19/2018 establece que los proveedores "
            "de servicios de pago deberan responder a las reclamaciones de los usuarios "
            "en un plazo maximo de 15 dias habiles desde la recepcion de la reclamacion. "
            "En circunstancias excepcionales, el plazo podra ampliarse a 35 dias habiles, "
            "informando al usuario de los motivos del retraso."
        ),
        expected_contexts=["Real Decreto-ley 19/2018", "Art. 48"],
        category="psd2",
        difficulty="easy",
    ),
    BenchmarkQuestion(
        question="Que regimen sancionador aplica a las entidades de pago en Espana?",
        ground_truth=(
            "Los articulos 70 a 77 del Real Decreto-ley 19/2018 regulan el regimen "
            "sancionador. Las infracciones muy graves pueden sancionarse con multa de "
            "hasta el 10% del volumen de negocios total anual, o con revocacion de la "
            "autorizacion. Las infracciones graves pueden conllevar multas de hasta "
            "el 5% del volumen de negocios. La competencia sancionadora corresponde "
            "al Banco de Espana para infracciones graves y muy graves."
        ),
        expected_contexts=["Real Decreto-ley 19/2018", "Art. 70"],
        category="psd2",
        difficulty="hard",
    ),
]

# ---------------------------------------------------------------------------
# Codigo Penal / Fraude (10 preguntas)
# ---------------------------------------------------------------------------

_PENAL_QUESTIONS: list[BenchmarkQuestion] = [
    BenchmarkQuestion(
        question="Como define el Codigo Penal espanol el delito de estafa?",
        ground_truth=(
            "El articulo 248 de la Ley Organica 10/1995 (Codigo Penal) define la estafa "
            "como: cometen estafa los que, con animo de lucro, utilizaren engano bastante "
            "para producir error en otro, induciendole a realizar un acto de disposicion "
            "en perjuicio propio o ajeno. La pena basica es de prision de 6 meses a "
            "3 anios, pudiendo agravarse segun el articulo 250."
        ),
        expected_contexts=["Codigo Penal", "Art. 248"],
        category="penal",
        difficulty="easy",
    ),
    BenchmarkQuestion(
        question="Que circunstancias agravan el delito de estafa?",
        ground_truth=(
            "El articulo 250 del Codigo Penal establece como agravantes: que recaiga "
            "sobre cosas de primera necesidad, viviendas u otros bienes de reconocida "
            "utilidad social; que se realice con simulacion de pleito o empleo de "
            "engano judicial; que se cometa abusando de firma en blanco o de las "
            "relaciones personales; que el valor de la defraudacion supere los "
            "50.000 euros; o que afecte a un elevado numero de personas."
        ),
        expected_contexts=["Codigo Penal", "Art. 250"],
        category="penal",
        difficulty="medium",
    ),
    BenchmarkQuestion(
        question="Como se tipifica el blanqueo de capitales en el Codigo Penal?",
        ground_truth=(
            "El articulo 301 del Codigo Penal tipifica el blanqueo de capitales: "
            "el que adquiera, posea, utilice, convierta o transmita bienes, sabiendo "
            "que tienen su origen en una actividad delictiva, o realice cualquier otro "
            "acto para ocultar o encubrir su origen ilicito, sera castigado con pena "
            "de prision de seis meses a seis anios y multa del tanto al triplo del "
            "valor de los bienes."
        ),
        expected_contexts=["Codigo Penal", "Art. 301"],
        category="penal",
        difficulty="easy",
    ),
    BenchmarkQuestion(
        question="Que penas aplica el Codigo Penal a la falsedad documental?",
        ground_truth=(
            "Los articulos 390 a 395 del Codigo Penal regulan la falsedad documental. "
            "El articulo 392 establece que el particular que cometiere falsedad en "
            "documento publico, oficial o mercantil sera castigado con pena de prision "
            "de seis meses a tres anios y multa de seis a doce meses. La falsedad en "
            "documento privado (articulo 395) se castiga con prision de seis meses a "
            "dos anios cuando se cause perjuicio a tercero."
        ),
        expected_contexts=["Codigo Penal", "Art. 390", "Art. 392"],
        category="penal",
        difficulty="medium",
    ),
    BenchmarkQuestion(
        question="Como regula el Codigo Penal los delitos informaticos de fraude?",
        ground_truth=(
            "El articulo 248.2 del Codigo Penal equipara a la estafa las manipulaciones "
            "informaticas o artificios semejantes que consigan una transferencia no "
            "consentida de cualquier activo patrimonial en perjuicio de otro. El "
            "articulo 249 establece penas de prision de 6 meses a 3 anios. El articulo "
            "197 bis y ter regulan el acceso ilicito a sistemas informaticos."
        ),
        expected_contexts=["Codigo Penal", "Art. 248"],
        category="penal",
        difficulty="medium",
    ),
    BenchmarkQuestion(
        question="Que contempla el Codigo Penal sobre la financiacion del terrorismo?",
        ground_truth=(
            "El articulo 576 del Codigo Penal tipifica la financiacion del terrorismo: "
            "sera castigado con pena de prision de 5 a 10 anios y multa del triple al "
            "quintuplo de su valor el que, por cualquier medio, directa o indirectamente, "
            "provea o recolecte fondos con la intencion de que se utilicen, o a sabiendas "
            "de que seran utilizados, para cometer cualquier delito de terrorismo."
        ),
        expected_contexts=["Codigo Penal", "Art. 576"],
        category="penal",
        difficulty="hard",
    ),
    BenchmarkQuestion(
        question=("Que responsabilidad penal tienen las personas juridicas por blanqueo?"),
        ground_truth=(
            "El articulo 302.2 del Codigo Penal, en relacion con el articulo 31 bis, "
            "establece la responsabilidad penal de las personas juridicas por blanqueo "
            "de capitales. Las penas incluyen multa de dos a cinco anios o del triple "
            "al quintuplo del valor de los bienes, disolucion, suspension de actividades, "
            "clausura de establecimientos, e inhabilitacion para obtener subvenciones."
        ),
        expected_contexts=["Codigo Penal", "Art. 302", "Art. 31 bis"],
        category="penal",
        difficulty="hard",
    ),
    BenchmarkQuestion(
        question="Que delitos regula el Codigo Penal contra el mercado y los consumidores?",
        ground_truth=(
            "Los articulos 281 a 286 del Codigo Penal regulan los delitos relativos "
            "al mercado y los consumidores, incluyendo: detraer del mercado materias "
            "primas o productos de primera necesidad (Art. 281), publicidad enganosa "
            "(Art. 282), facturacion ilicita (Art. 283), manipulacion de cotizaciones "
            "en mercados (Art. 284), uso de informacion privilegiada (Art. 285), y "
            "acceso ilicito a datos de un sistema informatico (Art. 286)."
        ),
        expected_contexts=["Codigo Penal", "Art. 284", "Art. 285"],
        category="penal",
        difficulty="medium",
    ),
    BenchmarkQuestion(
        question="Que pena tiene la apropiacion indebida en el Codigo Penal?",
        ground_truth=(
            "El articulo 253 del Codigo Penal castiga la apropiacion indebida: los que "
            "en perjuicio de otro, se apropiaren o distrajeren dinero, efectos, valores "
            "o cualquier otra cosa mueble que hubieran recibido en deposito, comision o "
            "administracion, seran castigados con las penas del articulo 249 (prision "
            "de 6 meses a 3 anios). Si excede de 50.000 euros, se aplican las penas "
            "del articulo 250."
        ),
        expected_contexts=["Codigo Penal", "Art. 253"],
        category="penal",
        difficulty="easy",
    ),
    BenchmarkQuestion(
        question="Como se regula la receptacion en el Codigo Penal?",
        ground_truth=(
            "El articulo 298 del Codigo Penal tipifica la receptacion: el que, con "
            "animo de lucro y con conocimiento de la comision de un delito contra el "
            "patrimonio o el orden socioeconomico, ayude a los responsables a "
            "aprovecharse de los efectos del mismo, o reciba, adquiera u oculte tales "
            "efectos, sera castigado con prision de seis meses a dos anios."
        ),
        expected_contexts=["Codigo Penal", "Art. 298"],
        category="penal",
        difficulty="medium",
    ),
]

# ---------------------------------------------------------------------------
# RGPD / Proteccion de datos (10 preguntas)
# ---------------------------------------------------------------------------

_RGPD_QUESTIONS: list[BenchmarkQuestion] = [
    BenchmarkQuestion(
        question=(
            "Cuales son las bases legitimas para el tratamiento de datos financieros segun el RGPD?"
        ),
        ground_truth=(
            "El articulo 6 del Reglamento (UE) 2016/679 (RGPD) establece seis bases "
            "legitimas: consentimiento del interesado, ejecucion de un contrato, "
            "cumplimiento de una obligacion legal, proteccion de intereses vitales, "
            "mision en interes publico, e interes legitimo. Para datos financieros "
            "en el contexto de prevencion de blanqueo, la base habitual es el "
            "cumplimiento de una obligacion legal (Ley 10/2010)."
        ),
        expected_contexts=["RGPD", "Art. 6", "Reglamento 2016/679"],
        category="rgpd",
        difficulty="easy",
    ),
    BenchmarkQuestion(
        question="Que derechos ARCO puede ejercer un cliente bancario segun el RGPD?",
        ground_truth=(
            "Los articulos 15 a 22 del RGPD reconocen los derechos de acceso (Art. 15), "
            "rectificacion (Art. 16), supresion o derecho al olvido (Art. 17), limitacion "
            "del tratamiento (Art. 18), portabilidad (Art. 20), oposicion (Art. 21) y "
            "decision individual automatizada incluyendo elaboracion de perfiles (Art. 22). "
            "En contexto bancario, el derecho de supresion puede limitarse cuando el "
            "tratamiento sea necesario para cumplir la Ley 10/2010 (conservacion 10 anios)."
        ),
        expected_contexts=["RGPD", "Art. 15", "Art. 17"],
        category="rgpd",
        difficulty="easy",
    ),
    BenchmarkQuestion(
        question=("Es obligatorio designar un DPO en entidades financieras?"),
        ground_truth=(
            "El articulo 37 del RGPD establece que debe designarse un Delegado de "
            "Proteccion de Datos cuando el tratamiento lo lleve a cabo una autoridad "
            "u organismo publico, o cuando las actividades principales requieran una "
            "observacion habitual y sistematica de interesados a gran escala. La Ley "
            "Organica 3/2018 (LOPDGDD), en su articulo 34.1.b, lo exige expresamente "
            "para entidades financieras, de credito, aseguradoras y reaseguradoras."
        ),
        expected_contexts=["RGPD", "Art. 37", "LOPDGDD", "Art. 34"],
        category="rgpd",
        difficulty="medium",
    ),
    BenchmarkQuestion(
        question="Que regula el RGPD sobre las decisiones automatizadas y el perfilado?",
        ground_truth=(
            "El articulo 22 del RGPD establece que todo interesado tiene derecho a no "
            "ser objeto de una decision basada unicamente en el tratamiento automatizado, "
            "incluida la elaboracion de perfiles, que produzca efectos juridicos o le "
            "afecte significativamente. Las excepciones son: si es necesaria para la "
            "celebracion de un contrato, si esta autorizada por el Derecho, o si se "
            "basa en el consentimiento explicito del interesado."
        ),
        expected_contexts=["RGPD", "Art. 22"],
        category="rgpd",
        difficulty="medium",
    ),
    BenchmarkQuestion(
        question=(
            "Que evaluacion de impacto (EIPD) debe realizarse para sistemas de deteccion de fraude?"
        ),
        ground_truth=(
            "El articulo 35 del RGPD exige una evaluacion de impacto relativa a la "
            "proteccion de datos cuando el tratamiento pueda entranar un alto riesgo "
            "para los derechos y libertades, incluyendo: evaluacion sistematica y "
            "exhaustiva de aspectos personales (perfilado), tratamiento a gran escala "
            "de datos sensibles, y vigilancia sistematica de zonas de acceso publico. "
            "Los sistemas de scoring de fraude basados en IA caen tipicamente bajo "
            "estas categorias."
        ),
        expected_contexts=["RGPD", "Art. 35"],
        category="rgpd",
        difficulty="hard",
    ),
    BenchmarkQuestion(
        question="Que obligaciones de notificacion de brechas establece el RGPD?",
        ground_truth=(
            "El articulo 33 del RGPD obliga al responsable a notificar a la autoridad "
            "de control competente (en Espana, la AEPD) una violacion de seguridad de "
            "datos personales en un plazo maximo de 72 horas desde que se tenga "
            "constancia. El articulo 34 exige tambien la comunicacion al interesado "
            "cuando la violacion entrane un alto riesgo para sus derechos y libertades."
        ),
        expected_contexts=["RGPD", "Art. 33", "Art. 34"],
        category="rgpd",
        difficulty="easy",
    ),
    BenchmarkQuestion(
        question="Que sanciones puede imponer la AEPD por incumplimiento del RGPD?",
        ground_truth=(
            "El articulo 83 del RGPD establece multas administrativas de hasta "
            "20.000.000 EUR o el 4% del volumen de negocio total anual global "
            "(la mayor de ambas cifras) para las infracciones mas graves. La Ley "
            "Organica 3/2018 (LOPDGDD), articulos 70 a 78, clasifica las infracciones "
            "en leves, graves y muy graves, con plazos de prescripcion de 1, 2 y 3 "
            "anios respectivamente."
        ),
        expected_contexts=["RGPD", "Art. 83", "LOPDGDD"],
        category="rgpd",
        difficulty="medium",
    ),
    BenchmarkQuestion(
        question=(
            "Que requisitos de proteccion de datos aplican a las transferencias internacionales?"
        ),
        ground_truth=(
            "Los articulos 44 a 49 del RGPD regulan las transferencias internacionales "
            "de datos. Solo pueden realizarse a paises con decisiones de adecuacion "
            "(Art. 45), o mediante garantias adecuadas como clausulas contractuales "
            "tipo (Art. 46), normas corporativas vinculantes (Art. 47), o excepciones "
            "especificas (Art. 49). Tras la anulacion del Privacy Shield (Schrems II), "
            "las entidades financieras deben aplicar medidas suplementarias."
        ),
        expected_contexts=["RGPD", "Art. 44", "Art. 46"],
        category="rgpd",
        difficulty="hard",
    ),
    BenchmarkQuestion(
        question=("Como se aplica el principio de minimizacion de datos en el contexto bancario?"),
        ground_truth=(
            "El articulo 5.1.c del RGPD establece el principio de minimizacion: los "
            "datos personales seran adecuados, pertinentes y limitados a lo necesario "
            "en relacion con los fines para los que son tratados. En el contexto "
            "bancario, esto implica recoger solo los datos estrictamente necesarios "
            "para la prestacion del servicio financiero y el cumplimiento de "
            "obligaciones legales (AML, KYC)."
        ),
        expected_contexts=["RGPD", "Art. 5"],
        category="rgpd",
        difficulty="easy",
    ),
    BenchmarkQuestion(
        question=(
            "Que obligaciones de privacidad por diseno impone el RGPD a sistemas de scoring?"
        ),
        ground_truth=(
            "El articulo 25 del RGPD establece la proteccion de datos desde el diseno "
            "y por defecto. El responsable debe aplicar medidas tecnicas y organizativas "
            "apropiadas, tanto en el momento de determinar los medios de tratamiento "
            "como en el propio tratamiento. Para sistemas de scoring de fraude, esto "
            "implica pseudonimizacion, limitacion del tratamiento, y accesibilidad "
            "de datos configurada al minimo por defecto."
        ),
        expected_contexts=["RGPD", "Art. 25"],
        category="rgpd",
        difficulty="hard",
    ),
]

# ---------------------------------------------------------------------------
# AI Act / Regulacion IA (10 preguntas)
# ---------------------------------------------------------------------------

_AI_ACT_QUESTIONS: list[BenchmarkQuestion] = [
    BenchmarkQuestion(
        question=("Como clasifica el AI Act los sistemas de IA utilizados en banca?"),
        ground_truth=(
            "El articulo 6 y el Anexo III del Reglamento (UE) 2024/1689 (AI Act) "
            "clasifican como sistemas de alto riesgo aquellos utilizados para evaluar "
            "la solvencia crediticia de personas fisicas (punto 5.b del Anexo III) y "
            "los utilizados para la evaluacion y clasificacion de riesgos en seguros "
            "de vida y salud. Los sistemas de deteccion de fraude bancario caen "
            "tipicamente en esta categoria de alto riesgo."
        ),
        expected_contexts=["AI Act", "Reglamento 2024/1689", "Anexo III"],
        category="ai_act",
        difficulty="medium",
    ),
    BenchmarkQuestion(
        question="Que obligaciones de transparencia impone el AI Act?",
        ground_truth=(
            "El articulo 13 del Reglamento (UE) 2024/1689 exige que los sistemas de "
            "IA de alto riesgo se disenan y desarrollen de forma que su funcionamiento "
            "sea suficientemente transparente para que los usuarios puedan interpretar "
            "los resultados del sistema y utilizarlos adecuadamente. Deben proporcionarse "
            "instrucciones de uso que incluyan las caracteristicas, capacidades y "
            "limitaciones del sistema."
        ),
        expected_contexts=["AI Act", "Reglamento 2024/1689", "Art. 13"],
        category="ai_act",
        difficulty="easy",
    ),
    BenchmarkQuestion(
        question="Que supervision humana requiere el AI Act para sistemas de alto riesgo?",
        ground_truth=(
            "El articulo 14 del Reglamento (UE) 2024/1689 exige que los sistemas de IA "
            "de alto riesgo se disenan y desarrollen de modo que puedan ser supervisados "
            "de forma efectiva por personas fisicas durante el periodo de uso. Las "
            "medidas de supervision humana deben permitir: comprender las capacidades "
            "y limitaciones del sistema, detectar anomalias y sesgos, poder interrumpir "
            "el sistema mediante un boton de parada o procedimiento similar, e intervenir "
            "en el resultado antes de que produzca efectos."
        ),
        expected_contexts=["AI Act", "Reglamento 2024/1689", "Art. 14"],
        category="ai_act",
        difficulty="medium",
    ),
    BenchmarkQuestion(
        question="Que sistema de gestion de riesgos exige el AI Act?",
        ground_truth=(
            "El articulo 9 del Reglamento (UE) 2024/1689 exige establecer, implementar, "
            "documentar y mantener un sistema de gestion de riesgos en relacion con "
            "los sistemas de IA de alto riesgo. Debe incluir: identificacion y analisis "
            "de riesgos conocidos y previsibles, estimacion y evaluacion de riesgos que "
            "puedan surgir, y adopcion de medidas de gestion de riesgos adecuadas. "
            "El sistema debe ser iterativo y actualizarse durante todo el ciclo de vida."
        ),
        expected_contexts=["AI Act", "Reglamento 2024/1689", "Art. 9"],
        category="ai_act",
        difficulty="medium",
    ),
    BenchmarkQuestion(
        question="Que requisitos de gobernanza de datos establece el AI Act?",
        ground_truth=(
            "El articulo 10 del Reglamento (UE) 2024/1689 establece que los conjuntos "
            "de datos de entrenamiento, validacion y prueba deben estar sujetos a "
            "practicas de gobernanza adecuadas, incluyendo: diseno pertinente, "
            "representatividad y libre de errores en la medida de lo posible, "
            "completitud respecto al uso previsto, y examen previo de posibles sesgos. "
            "Los conjuntos de datos deben tener en cuenta las caracteristicas "
            "especificas del entorno geografico y contextual."
        ),
        expected_contexts=["AI Act", "Reglamento 2024/1689", "Art. 10"],
        category="ai_act",
        difficulty="hard",
    ),
    BenchmarkQuestion(
        question="Que obligaciones de registro impone el AI Act a sistemas de alto riesgo?",
        ground_truth=(
            "El articulo 49 del Reglamento (UE) 2024/1689 establece que antes de "
            "la comercializacion o puesta en servicio, los proveedores de sistemas "
            "de IA de alto riesgo deben registrar el sistema en la base de datos "
            "de la UE accesible al publico. El articulo 12 exige ademas que los "
            "sistemas generen registros automaticos (logs) que permitan trazabilidad "
            "durante su funcionamiento."
        ),
        expected_contexts=["AI Act", "Reglamento 2024/1689", "Art. 49", "Art. 12"],
        category="ai_act",
        difficulty="hard",
    ),
    BenchmarkQuestion(
        question="Que practicas de IA estan prohibidas por el AI Act?",
        ground_truth=(
            "El articulo 5 del Reglamento (UE) 2024/1689 prohibe: sistemas de "
            "manipulacion subliminal o enganosa, sistemas que exploten vulnerabilidades "
            "de grupos especificos, sistemas de puntuacion social (social scoring) "
            "por parte de autoridades publicas, sistemas de identificacion biometrica "
            "remota en tiempo real en espacios publicos para fines de aplicacion de "
            "la ley (salvo excepciones), y sistemas de categorizacion biometrica "
            "basados en caracteristicas sensibles."
        ),
        expected_contexts=["AI Act", "Reglamento 2024/1689", "Art. 5"],
        category="ai_act",
        difficulty="easy",
    ),
    BenchmarkQuestion(
        question="Que sanciones establece el AI Act por incumplimiento?",
        ground_truth=(
            "El articulo 99 del Reglamento (UE) 2024/1689 establece multas de hasta "
            "35.000.000 EUR o el 7% del volumen de negocio anual total mundial (la "
            "mayor de ambas) por el uso de practicas prohibidas. Para incumplimiento "
            "de requisitos de alto riesgo, las multas pueden alcanzar 15.000.000 EUR "
            "o el 3% del volumen de negocio. Para informacion incorrecta a las "
            "autoridades, hasta 7.500.000 EUR o el 1% del volumen de negocio."
        ),
        expected_contexts=["AI Act", "Reglamento 2024/1689", "Art. 99"],
        category="ai_act",
        difficulty="medium",
    ),
    BenchmarkQuestion(
        question="Que obligaciones tiene el deployer de IA segun el AI Act?",
        ground_truth=(
            "El articulo 26 del Reglamento (UE) 2024/1689 establece que los "
            "responsables del despliegue (deployers) de sistemas de alto riesgo deben: "
            "utilizar el sistema conforme a las instrucciones de uso, garantizar que "
            "los datos de entrada sean pertinentes, asignar la supervision humana a "
            "personas con la competencia necesaria, monitorizar el funcionamiento, "
            "e informar al proveedor de incidentes graves o mal funcionamiento."
        ),
        expected_contexts=["AI Act", "Reglamento 2024/1689", "Art. 26"],
        category="ai_act",
        difficulty="medium",
    ),
    BenchmarkQuestion(
        question="Que establece el AI Act sobre la evaluacion de conformidad?",
        ground_truth=(
            "El articulo 43 del Reglamento (UE) 2024/1689 establece que los sistemas "
            "de IA de alto riesgo deben someterse a una evaluacion de conformidad "
            "antes de su comercializacion. Segun el tipo de sistema, puede ser "
            "autoevaluacion basada en control interno de produccion (Anexo VI) o "
            "evaluacion por un organismo notificado (Anexo VII). Los sistemas de "
            "scoring crediticio requieren evaluacion por organismo notificado."
        ),
        expected_contexts=["AI Act", "Reglamento 2024/1689", "Art. 43"],
        category="ai_act",
        difficulty="hard",
    ),
]

# ---------------------------------------------------------------------------
# Benchmark completo: 50 preguntas
# ---------------------------------------------------------------------------

FRAUD_BENCHMARK: list[BenchmarkQuestion] = [
    *_AML_QUESTIONS,
    *_PSD2_QUESTIONS,
    *_PENAL_QUESTIONS,
    *_RGPD_QUESTIONS,
    *_AI_ACT_QUESTIONS,
]
