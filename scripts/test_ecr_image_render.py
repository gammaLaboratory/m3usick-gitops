#!/usr/bin/env python3
"""Regression tests for deploying immutable m3usick ECR images."""

from __future__ import annotations

import copy
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ECR_REPOSITORY = "004908959120.dkr.ecr.ap-northeast-1.amazonaws.com/m3usick"
TEST_TAG = "0123456789abcdef"


def deployment_from_documents(documents: list[dict]) -> dict:
    return next(
        document
        for document in documents
        if document and document.get("kind") == "Deployment"
        and document.get("metadata", {}).get("name") == "m3usick-web"
    )


class EcrImageDeploymentTest(unittest.TestCase):
    def test_base_runs_prebuilt_image_without_checkout_init_container(self) -> None:
        deployment = yaml.safe_load((ROOT / "app/base/deployment.yaml").read_text())
        pod_spec = deployment["spec"]["template"]["spec"]
        self.assertNotIn("initContainers", pod_spec)
        self.assertEqual(pod_spec["imagePullSecrets"], [{"name": "ecr-secret"}])

        self.assertEqual(len(pod_spec["containers"]), 1)
        container = pod_spec["containers"][0]
        self.assertEqual(container["image"], "m3usick-web")
        self.assertNotIn("command", container)
        self.assertNotIn("workingDir", container)
        self.assertNotIn("volumeMounts", container)
        self.assertNotIn("volumes", pod_spec)

    def test_each_overlay_renders_requested_ecr_image(self) -> None:
        for environment in ("dev", "prod"):
            with self.subTest(environment=environment), tempfile.TemporaryDirectory() as tmp:
                app = Path(tmp) / "app"
                subprocess.run(
                    ["cp", "-a", str(ROOT / "app/."), str(app)],
                    check=True,
                )
                kustomization = app / "overlays" / environment / "kustomization.yaml"
                config = yaml.safe_load(kustomization.read_text())
                config["images"] = [
                    {
                        "name": "m3usick-web",
                        "newName": ECR_REPOSITORY,
                        "newTag": TEST_TAG,
                    }
                ]
                kustomization.write_text(yaml.safe_dump(config, sort_keys=False))

                rendered = subprocess.run(
                    ["kubectl", "kustomize", str(kustomization.parent)],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout
                deployment = deployment_from_documents(list(yaml.safe_load_all(rendered)))
                pod_spec = deployment["spec"]["template"]["spec"]
                self.assertEqual(
                    pod_spec["containers"][0]["image"],
                    f"{ECR_REPOSITORY}:{TEST_TAG}",
                )
                self.assertNotIn("initContainers", pod_spec)


if __name__ == "__main__":
    unittest.main()
