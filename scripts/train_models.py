"""
OceanEye - Master AI Model Training & Registry Orchestrator
Coordinates training, validation, and serialization across the three OceanEye AI models:
  1. SAR Oil-Spill Segmentation (PyTorch U-Net)
  2. Look-Alike Classifier (XGBoost)
  3. AIS Vessel Prioritization & Ranking (XGBoost)
"""

import argparse
import sys
from pathlib import Path
from typing import Any

# Add scripts directory to sys.path
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from common import get_event, setup_logging
from models.classification.train import train_classification_model
from models.common import get_model_dir
from models.ranking.train import train_ranking_model
from models.segmentation.train import train_segmentation_model


def print_header(event_name: str, event_info: dict, model_choice: str, use_synthetic: bool):
    print()
    print("=" * 80)
    print("OCEANEYE - AI MODEL TRAINING & REGISTRY PIPELINE")
    print("=" * 80)
    print(f"Target Event : {event_info.get('name', event_name)} ({event_name})")
    print(f"Coordinates  : lat {event_info.get('latitude')}, lon {event_info.get('longitude')}")
    print(f"Model Scope  : {model_choice.upper()}")
    print(f"Data Mode    : {'SYNTHETIC TEST BENCHMARK' if use_synthetic else 'OPERATIONAL / SPECIFIED DATASET'}")
    print("=" * 80)
    print()


def print_summary_card(title: str, result: dict[str, Any]):
    status = result.get("status", "unknown")
    status_display = {
        "success": "[SUCCESS] Model Trained & Checkpointed",
        "skipped": "[SKIPPED] Missing Training Data",
        "failed": "[FAILED] Training Encountered Errors",
    }.get(status, f"[{status.upper()}]")

    print(f"--- {title} ---")
    print(f"Status        : {status_display}")
    if "is_synthetic" in result:
        data_tag = "SYNTHETIC TEST DATA (Pipeline verification only)" if result["is_synthetic"] else "REAL DATASET"
        print(f"Data Origin   : {data_tag}")
    if "weights_file" in result:
        print(f"Weights File  : {result['weights_file']}")
    if "model_file" in result:
        print(f"Artifact File : {result['model_file']}")
    if "metadata_file" in result:
        print(f"Metadata File : {result['metadata_file']}")

    metrics = result.get("metrics", {})
    if metrics:
        metric_str = " | ".join([f"{k}: {v}" for k, v in metrics.items() if not isinstance(v, (list, dict))])
        print(f"Metrics       : {metric_str}")

    if "top_features" in result:
        top_feats = ", ".join([f"{k} ({v})" for k, v in result["top_features"][:3]])
        print(f"Key Features  : {top_feats}")

    if "error" in result:
        print(f"Error Details : {result['error']}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="OceanEye AI Model Training, Validation & Registry CLI"
    )

    parser.add_argument(
        "--model",
        default="all",
        choices=["all", "segmentation", "classification", "ranking"],
        help="Target AI model to train (default: all)",
    )

    parser.add_argument(
        "--event",
        default="wakashio",
        help="Target event from config/events.json (default: wakashio)",
    )

    parser.add_argument(
        "--data",
        default=None,
        help="Path to custom training dataset directory or CSV file",
    )

    parser.add_argument(
        "--output",
        default=None,
        help="Custom output directory for model checkpoints (default: models/<model_type>/)",
    )

    parser.add_argument(
        "--epochs",
        type=int,
        default=5,
        help="Number of epochs for deep learning segmentation model (default: 5)",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=4,
        help="Batch size for segmentation training (default: 4)",
    )

    parser.add_argument(
        "--use-synthetic",
        action="store_true",
        help="Run pipeline verification using synthetic benchmark datasets",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing trained model checkpoints if present",
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )

    args = parser.parse_args()

    logger = setup_logging("train_models", args.log_level)

    # Validate target event (exits cleanly with code 1 if invalid)
    event_info = get_event(args.event)

    print_header(args.event, event_info, args.model, args.use_synthetic)

    results: dict[str, dict[str, Any]] = {}
    has_failure = False

    # 1. Dispatch SAR Oil-Spill Segmentation (U-Net)
    if args.model in ("all", "segmentation"):
        logger.info("Initializing SAR Oil-Spill Segmentation training...")
        try:
            res = train_segmentation_model(
                data_dir=args.data,
                output_dir=args.output,
                epochs=args.epochs,
                batch_size=args.batch_size,
                use_synthetic=args.use_synthetic or (args.data is None),
                logger=logger,
            )
            results["SAR Oil-Spill Segmentation (PyTorch U-Net)"] = res
            if res.get("status") == "failed":
                has_failure = True
        except Exception as exc:
            logger.error("Segmentation training failed: %s", exc, exc_info=True)
            results["SAR Oil-Spill Segmentation (PyTorch U-Net)"] = {
                "status": "failed",
                "error": str(exc),
            }
            has_failure = True

    # 2. Dispatch Look-Alike Classifier (XGBoost)
    if args.model in ("all", "classification"):
        logger.info("Initializing Look-Alike Classifier training...")
        try:
            res = train_classification_model(
                data_path=args.data,
                output_dir=args.output,
                use_synthetic=args.use_synthetic or (args.data is None),
                logger=logger,
            )
            results["Look-Alike Classifier (XGBoost)"] = res
            if res.get("status") == "failed":
                has_failure = True
        except Exception as exc:
            logger.error("Classification training failed: %s", exc, exc_info=True)
            results["Look-Alike Classifier (XGBoost)"] = {
                "status": "failed",
                "error": str(exc),
            }
            has_failure = True

    # 3. Dispatch Vessel Prioritization & Ranking Model (XGBoost)
    if args.model in ("all", "ranking"):
        logger.info("Initializing Vessel Prioritization & Ranking model training...")
        try:
            res = train_ranking_model(
                data_path=args.data,
                output_dir=args.output,
                use_synthetic=args.use_synthetic or (args.data is None),
                logger=logger,
            )
            results["Vessel Prioritization & Ranking (XGBoost)"] = res
            if res.get("status") == "failed":
                has_failure = True
        except Exception as exc:
            logger.error("Vessel ranking training failed: %s", exc, exc_info=True)
            results["Vessel Prioritization & Ranking (XGBoost)"] = {
                "status": "failed",
                "error": str(exc),
            }
            has_failure = True

    # Output Summary Report
    print("=" * 80)
    print("MODEL TRAINING & REGISTRY SUMMARY REPORT")
    print("=" * 80)
    for title, res in results.items():
        print_summary_card(title, res)
    print("=" * 80)

    if any(r.get("is_synthetic", False) for r in results.values()):
        print("SCIENTIFIC HONESTY NOTICE:")
        print("One or more models were trained on SYNTHETIC benchmark distributions for pipeline")
        print("verification. They are intended for architecture testing and MUST NOT be represented")
        print("as operational models trained on labeled real-world satellite ground-truth.")
        print("=" * 80)

    if has_failure:
        logger.error("One or more AI model pipelines failed.")
        sys.exit(1)
    else:
        logger.info("AI model training execution completed successfully.")


if __name__ == "__main__":
    main()
