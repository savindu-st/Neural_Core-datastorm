import subprocess
import sys
import logging
import os
import socket
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger("QuadNovaPipeline")

def run_script(script_path):
    logger.info(f"🚀 Starting: {script_path}")
    import os
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    
    try:
        result = subprocess.run([sys.executable, script_path], check=True, text=True, capture_output=True, env=env)
        logger.info(f"✅ Completed: {script_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed: {script_path}")
        logger.error(f"Error Output:\n{e.stderr}")
        return False

def main():
    logger.info("========================================")
    logger.info("QuadNova Data Storm Pipeline Runner")
    logger.info("========================================")

    scripts = [
        # 1. Data Engineering -1
        "src/data_pipeline/ingest.py",
        "src/data_pipeline/clean.py",
        
        # 2. Scrapers -1
        "src/scraper/poi_fast_scraper.py",
        "src/scraper/competitor_scraper.py",
        
        # 3. Spatial Intelligence -1
        "src/spatial/distance_decay.py",
        "src/spatial/catchment_density.py",
        
        # 4. Feature Engineering -2
        "src/features/seasonality_features.py",
        "src/features/sales_features.py",
        "src/features/spatial_features.py",
        "src/features/build_features.py",
        
        # 5. Modeling -2
        "src/models/train_model.py",
        "src/models/predict.py",
        "src/models/calibrate_potential.py",
        "src/models/model_interpretability.py",
        "src/features/outlet_segmentation.py",
        
        # 6. Budget Optimization -2
        "src/optimization/roi_calculator.py",
        "src/optimization/budget_optimizer.py",
        
        # 6.5 Visualizations & Evidence
        "src/utils/generate_evidence.py",
        "src/utils/generate_visuals.py",
        
        # 7. Explainable AI -3
        "src/xai/outlet_reasoning.py",
        "src/xai/genai_explainer.py",
    ]

    for script in scripts:
        success = run_script(script)
        if not success:
            logger.error("🛑 Pipeline stopped due to an error.")
            sys.exit(1)
            
    logger.info("🎉 SUCCESS! All pipeline steps completed.")
    logger.info("Predictions available at: outputs/predictions/quadnova_predictions.csv")
    logger.info("Allocations available at: outputs/predictions/quadnova_budget_allocations.csv")
    
    logger.info("")
    logger.info("========================================")
    logger.info("🌐 Starting QuadNova Web Application...")
    logger.info("========================================")

    
    # Determine free ports for backend and frontend
    bp_str = os.getenv("QUADNOVA_PORT", "")
    backend_port = int(bp_str) if bp_str.isdigit() else None
    
    def _free(start):
        p = start
        while True:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(("localhost", p)) != 0:
                    return p
            p += 1

    if not backend_port:
        # find free port starting at 8000
        backend_port = _free(8000)
        os.environ["QUADNOVA_PORT"] = str(backend_port)
        
    fp_str = os.getenv("VITE_PORT", "")
    frontend_port = int(fp_str) if fp_str.isdigit() else None
    if not frontend_port:
        frontend_port = _free(3000)
        os.environ["VITE_PORT"] = str(frontend_port)

    backend = subprocess.Popen(
        [sys.executable, "webapp/api/main.py"],
        env=env,
        cwd=os.getcwd()
    )
    
    logger.info(f"🚀 Starting Frontend App (http://localhost:{frontend_port})...")
    frontend = subprocess.Popen(
        ["npm", "run", "dev", "--", "--port", str(frontend_port)],
        cwd=os.path.join(os.getcwd(), "webapp", "frontend"),
        env=os.environ.copy(),
        shell=True
    )
    
    logger.info("")
    logger.info("✅ QuadNova is now running!")
    logger.info(f"   📊 Dashboard:  http://localhost:{frontend_port}")
    logger.info("")
    logger.info("Press Ctrl+C to stop all services.")
    
    try:
        backend.wait()
    except KeyboardInterrupt:
        logger.info("\n🛑 Shutting down QuadNova...")
        backend.terminate()
        frontend.terminate()
        backend.wait()
        frontend.wait()
        logger.info("👋 QuadNova stopped. Goodbye!")

if __name__ == "__main__":
    main()
