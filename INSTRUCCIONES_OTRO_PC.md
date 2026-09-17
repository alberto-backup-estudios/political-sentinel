# Guía de Continuidad y Sincronización Multi-PC — Political Sentinel

Este documento contiene las instrucciones paso a paso para configurar este proyecto en tu otro PC (oficina o casa) y mantener la sincronización fluida y automática en el día a día.

---

## 🚀 Paso 1: Configuración Inicial (Solo la primera vez en el otro PC)

Cuando abras el segundo PC por primera vez, ejecuta estos comandos en una ventana de **PowerShell**:

### 1.1 Clonar el repositorio y actualizar el contexto
```powershell
# 1. Navegar a tu directorio base
cd C:\Claude

# 2. Clonar este nuevo repositorio
git clone https://github.com/alberto-backup-estudios/political-sentinel.git

# 3. Actualizar claude-context para tener las instrucciones y el sincronizador al día
cd C:\Claude\claude-context
git pull origin main
```

### 1.2 Actualizar el script `sincronizar.ps1` en la raíz de `C:\Claude`
Para asegurarte de que `C:\Claude\sincronizar.ps1` en ese PC reconozca `political-sentinel`, copia la versión actualizada desde `claude-context`:
```powershell
Copy-Item "C:\Claude\claude-context\manuales\sincronizar.ps1" -Destination "C:\Claude\sincronizar.ps1" -Force
```

### 1.3 Crear el entorno virtual Python (Ligero y local)
Para mantener el PC liviano y ordenado (el `.gitignore` ya está configurado para ignorar la carpeta `venv/`):
```powershell
cd C:\Claude\political-sentinel
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 🔄 Paso 2: Flujo de Trabajo Diario (Rutina Habitual)

A partir de la configuración inicial, nunca más tendrás que clonar nada. Tu rutina diaria será:

### Al llegar al PC (al iniciar el trabajo):
Trae los cambios más recientes que hiciste en la otra máquina:
```powershell
cd C:\Claude
powershell -ExecutionPolicy Bypass -File .\sincronizar.ps1 pull
```

### Al terminar la jornada en el PC:
Guarda tus cambios con commit en cada repo donde trabajaste y súbelos todos a GitHub con:
```powershell
cd C:\Claude
powershell -ExecutionPolicy Bypass -File .\sincronizar.ps1 push
```

---

## 📂 Dónde Quedó Todo el Material de Consulta

* `conversacion_completa.md`: Registro íntegro del diseño conceptual, viabilidad técnica, consultas de APIs del Congreso e inspiración en scorecards internacionales (NFIB, ADA, CAP, NOMINATE).
* `metodologia_y_mapas.md`: Marco matemático formal, definición del vector 6D $\vec{L}$, ponderaciones del voto, reducción a coordenadas 2D $(X_i, Y_i)$, centroides partidarios y elipses de disciplina.
* `schemas/taxonomia_leyes.json`: Esquema JSON estructurado para clasificar los proyectos de ley con IA y datos de DIPRES/CNEP.
* `src/extractor_camara.py`: Extractor funcional en Python para la API de datos abiertos de la Cámara de Diputadas y Diputados (`opendata.camara.cl`).

---

## 🎯 Próximos Pasos para Retomar el Lunes

1. **Extractor para el Senado:** Desarrollar el script espejo para consumir los datos de `tramitacion.senado.cl`.
2. **Clasificación de Leyes Emblemáticas:** Seleccionar los primeros 5 proyectos clave (ej: 40 Horas, Royalty Minero, PGU, Ley Karin, Reforma Tributaria) y obtener sus vectores de impacto.
3. **Motor de Cálculo:** Implementar las fórmulas de `metodologia_y_mapas.md` para situar a los parlamentarios y bancadas en los 4 cuadrantes.
4. **Dashboard Visual:** Generar la interfaz web interactiva para visualizar los mapas.
