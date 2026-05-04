import hashlib
import json
import os
from uuid import uuid4

from django.utils import timezone

from ..models import ProcurementConfigPublication, ProcurementConfigPublishRequest
from .config_service import ProcurementConfigService


class ProcurementConfigGovernanceService:
    GOVERNED_ASSETS = ("rules", "ranking", "policy", "templates")
    PUBLISH_WORKFLOW = "engineering_controlled_publish"
    ROLLBACK_MODE = "version_pinned_metadata_only"
    PROPOSAL_WORKFLOW = "audited_proposal_input"
    ENGINEERING_PUBLISH_TOKEN_ENV = "PROCUREMENT_CONFIG_PUBLISH_TOKEN"

    def __init__(self, config_service=None):
        self.config_service = config_service or ProcurementConfigService()

    def ensure_publish_history(self, assets=None):
        asset_snapshots = self._build_asset_snapshots(assets=assets)
        current_publications = {}
        for asset_name, snapshot in asset_snapshots.items():
            current_publications[asset_name] = self._ensure_asset_publication(asset_name, snapshot, asset_snapshots)
        return current_publications

    def get_publish_summary(self, history_limit=10):
        history_limit = max(int(history_limit or 10), 1)
        self.ensure_publish_history()
        publications = list(
            ProcurementConfigPublication.objects.filter(asset_type__in=self.GOVERNED_ASSETS).order_by(
                "asset_type", "-created_at", "-id"
            )
        )
        history = {}
        current_assets = {}
        for asset_name in self.GOVERNED_ASSETS:
            asset_publications = [record for record in publications if record.asset_type == asset_name]
            current_publication = self._get_current_publication(asset_name)
            if current_publication:
                current_assets[asset_name] = self._serialize_publication(current_publication)
            history[asset_name] = [
                self._serialize_publication(record) for record in asset_publications[:history_limit]
            ]

        return {
            "governed_assets": list(self.GOVERNED_ASSETS),
            "publish_workflow": self.PUBLISH_WORKFLOW,
            "proposal_workflow": self.PROPOSAL_WORKFLOW,
            "rollback_mode": self.ROLLBACK_MODE,
            "current_assets": current_assets,
            "history": history,
        }

    def get_publish_workflow_summary(self, history_limit=10, pending_limit=10, assets=None):
        summary = self.get_publish_summary(history_limit=history_limit)
        pending_limit = max(int(pending_limit or 10), 1)
        pending_requests = [
            self._serialize_publish_request(request)
            for request in ProcurementConfigPublishRequest.objects.filter(
                status="pending_engineering_review",
                action_type="publish",
            )[
                :pending_limit
            ]
        ]
        summary.update(
            {
                "engineering_controlled": True,
                "publishable_assets": self.preview_publishable_assets(assets=assets),
                "pending_requests": pending_requests,
                "execution_contract": {
                    "execute_endpoint_requires_token": True,
                    "token_header": "X-Procurement-Config-Publish-Token",
                    "actor_header": "X-User-Id",
                    "proposal_required_before_publish": True,
                },
            }
        )
        return summary

    def get_rollback_workflow_summary(self, history_limit=10, pending_limit=10, assets=None):
        summary = self.get_publish_summary(history_limit=history_limit)
        pending_limit = max(int(pending_limit or 10), 1)
        pending_requests = [
            self._serialize_publish_request(request)
            for request in ProcurementConfigPublishRequest.objects.filter(
                status="pending_engineering_review",
                action_type="rollback",
            )[:pending_limit]
        ]
        summary.update(
            {
                "engineering_controlled": True,
                "rollbackable_assets": self.preview_rollbackable_assets(assets=assets),
                "pending_requests": pending_requests,
                "execution_contract": {
                    "execute_endpoint_requires_token": True,
                    "token_header": "X-Procurement-Config-Publish-Token",
                    "actor_header": "X-User-Id",
                    "proposal_required_before_rollback": True,
                },
            }
        )
        return summary

    def preview_publishable_assets(self, assets=None):
        snapshots = self._build_asset_snapshots(assets=assets)
        pending_requests = list(
            ProcurementConfigPublishRequest.objects.filter(
                status="pending_engineering_review",
                action_type="publish",
            )
        )
        preview = {}
        for asset_name, snapshot in snapshots.items():
            current_publication = self._get_current_publication(asset_name)
            if not current_publication:
                change_state = "bootstrap_publish_required"
                publishable = True
                version_changed = bool(snapshot["version"])
                checksum_changed = True
            else:
                self._backfill_publication_snapshot(current_publication, snapshot=snapshot, governed_snapshots=snapshots)
                version_changed = current_publication.asset_version != snapshot["version"]
                checksum_changed = current_publication.file_checksum != snapshot["checksum"]
                change_state = "publishable_change" if version_changed or checksum_changed else "already_published"
                publishable = change_state != "already_published"

            preview[asset_name] = {
                "asset_type": asset_name,
                "candidate_version": snapshot["version"],
                "candidate_checksum": snapshot["checksum"],
                "current_publication_id": current_publication.publication_id if current_publication else "",
                "current_published_version": current_publication.asset_version if current_publication else "",
                "current_published_checksum": current_publication.file_checksum if current_publication else "",
                "publishable": publishable,
                "change_state": change_state,
                "diff_summary": {
                    "version_changed": version_changed,
                    "checksum_changed": checksum_changed,
                },
                "requires_engineering_approval": True,
                "pending_request_ids": [
                    request.request_id for request in pending_requests if asset_name in list(request.asset_types or [])
                ],
                "rollback_target": {
                    "publication_id": current_publication.publication_id if current_publication else "",
                    "version": current_publication.asset_version if current_publication else "",
                    "available": bool(current_publication),
                },
            }
        return preview

    def preview_rollbackable_assets(self, assets=None):
        asset_names = list(assets or self.GOVERNED_ASSETS)
        pending_requests = list(
            ProcurementConfigPublishRequest.objects.filter(
                status="pending_engineering_review",
                action_type="rollback",
            )
        )
        preview = {}
        for asset_name in asset_names:
            if asset_name not in self.GOVERNED_ASSETS:
                raise ValueError(f"Unsupported governed asset: {asset_name}")
            current_publication = self._get_current_publication(asset_name)
            rollback_target = None
            if current_publication and current_publication.rollback_target_publication_id:
                rollback_target = ProcurementConfigPublication.objects.filter(
                    publication_id=current_publication.rollback_target_publication_id
                ).first()
            target_snapshot = dict((rollback_target.meta or {}).get("config_snapshot") or {}) if rollback_target else {}
            preview[asset_name] = {
                "asset_type": asset_name,
                "current_publication_id": current_publication.publication_id if current_publication else "",
                "current_published_version": current_publication.asset_version if current_publication else "",
                "rollback_supported": bool(rollback_target and target_snapshot),
                "change_state": "rollback_ready" if rollback_target and target_snapshot else "rollback_unavailable",
                "target_publication_id": rollback_target.publication_id if rollback_target else "",
                "target_version": rollback_target.asset_version if rollback_target else "",
                "target_checksum": rollback_target.file_checksum if rollback_target else "",
                "pending_request_ids": [
                    request.request_id for request in pending_requests if asset_name in list(request.asset_types or [])
                ],
            }
        return preview

    def create_publish_request(self, asset_types=None, requested_by="", proposal_source="", reason="", notes=""):
        preview = self.preview_publishable_assets(assets=asset_types)
        publishable_assets = {
            asset_name: snapshot for asset_name, snapshot in preview.items() if snapshot.get("publishable")
        }
        if not publishable_assets:
            raise ValueError("No unpublished config changes are available to publish.")

        reason = str(reason or "").strip()
        if not reason:
            raise ValueError("A publish reason is required for audited config changes.")

        request = ProcurementConfigPublishRequest.objects.create(
            request_id=str(uuid4()),
            action_type="publish",
            status="pending_engineering_review",
            asset_types=list(publishable_assets.keys()),
            requested_by=str(requested_by or "").strip(),
            proposal_source=str(proposal_source or "engineering").strip() or "engineering",
            reason=reason,
            notes=str(notes or "").strip(),
            requested_snapshot=publishable_assets,
            meta={
                "publish_workflow": self.PUBLISH_WORKFLOW,
                "proposal_workflow": self.PROPOSAL_WORKFLOW,
                "rollback_mode": self.ROLLBACK_MODE,
            },
        )
        return self._serialize_publish_request(request)

    def create_rollback_request(self, asset_types=None, requested_by="", proposal_source="", reason="", notes=""):
        preview = self.preview_rollbackable_assets(assets=asset_types)
        rollbackable_assets = {
            asset_name: snapshot for asset_name, snapshot in preview.items() if snapshot.get("rollback_supported")
        }
        if not rollbackable_assets:
            raise ValueError("No rollback-ready config publications are available.")

        reason = str(reason or "").strip()
        if not reason:
            raise ValueError("A rollback reason is required for audited config changes.")

        request = ProcurementConfigPublishRequest.objects.create(
            request_id=str(uuid4()),
            action_type="rollback",
            status="pending_engineering_review",
            asset_types=list(rollbackable_assets.keys()),
            requested_by=str(requested_by or "").strip(),
            proposal_source=str(proposal_source or "engineering").strip() or "engineering",
            reason=reason,
            notes=str(notes or "").strip(),
            requested_snapshot=rollbackable_assets,
            meta={
                "publish_workflow": self.PUBLISH_WORKFLOW,
                "proposal_workflow": self.PROPOSAL_WORKFLOW,
                "rollback_mode": self.ROLLBACK_MODE,
            },
        )
        return self._serialize_publish_request(request)

    def execute_publish_request(self, request_id, authorization_token="", executed_by=""):
        self._require_engineering_publish_token(authorization_token)
        request = ProcurementConfigPublishRequest.objects.filter(request_id=request_id).first()
        if not request:
            raise ValueError("Unknown config publish request.")
        if request.action_type != "publish":
            raise ValueError("Requested workflow is not a publish request.")
        if request.status != "pending_engineering_review":
            raise ValueError("Only pending engineering review requests can be published.")

        requested_snapshot = dict(request.requested_snapshot or {})
        current_preview = self.preview_publishable_assets(assets=request.asset_types)
        stale_assets = []
        for asset_name, snapshot in requested_snapshot.items():
            current_asset = current_preview.get(asset_name) or {}
            if (
                current_asset.get("candidate_version") != snapshot.get("candidate_version")
                or current_asset.get("candidate_checksum") != snapshot.get("candidate_checksum")
                or not current_asset.get("publishable")
            ):
                stale_assets.append(asset_name)
        if stale_assets:
            request.status = "stale_request"
            request.meta = dict(request.meta or {})
            request.meta["stale_assets"] = stale_assets
            request.save(update_fields=["status", "meta", "updated_at"])
            raise ValueError("Publish request is stale because governed assets changed after proposal creation.")

        asset_snapshots = self._build_asset_snapshots(assets=request.asset_types)
        publications = []
        for asset_name in request.asset_types:
            publication = self._ensure_asset_publication(
                asset_name,
                asset_snapshots[asset_name],
                asset_snapshots,
                publish_source="engineering_publish_workflow",
                request_context={
                    "request_id": request.request_id,
                    "requested_by": request.requested_by,
                    "proposal_source": request.proposal_source,
                    "reason": request.reason,
                    "notes": request.notes,
                    "executed_by": str(executed_by or "").strip(),
                },
            )
            publications.append(publication)

        request.status = "published"
        request.executed_by = str(executed_by or "").strip()
        request.executed_at = timezone.now()
        request.published_publication_ids = [publication.publication_id for publication in publications]
        request.meta = dict(request.meta or {})
        request.meta["published_assets"] = {
            publication.asset_type: publication.publication_id for publication in publications
        }
        request.save(
            update_fields=[
                "status",
                "executed_by",
                "executed_at",
                "published_publication_ids",
                "meta",
                "updated_at",
            ]
        )
        return {
            "request": self._serialize_publish_request(request),
            "publications": [self._serialize_publication(publication) for publication in publications],
        }

    def execute_rollback_request(self, request_id, authorization_token="", executed_by=""):
        self._require_engineering_publish_token(authorization_token)
        request = ProcurementConfigPublishRequest.objects.filter(request_id=request_id).first()
        if not request:
            raise ValueError("Unknown config rollback request.")
        if request.action_type != "rollback":
            raise ValueError("Requested workflow is not a rollback request.")
        if request.status != "pending_engineering_review":
            raise ValueError("Only pending engineering review requests can be rolled back.")

        requested_snapshot = dict(request.requested_snapshot or {})
        rollback_targets = {}
        stale_assets = []
        validation_failures = []
        for asset_name, snapshot in requested_snapshot.items():
            current_publication = self._get_current_publication(asset_name)
            if not current_publication or current_publication.publication_id != snapshot.get("current_publication_id"):
                stale_assets.append(asset_name)
                continue
            target_publication = ProcurementConfigPublication.objects.filter(
                publication_id=snapshot.get("target_publication_id")
            ).first()
            target_config_snapshot = dict((target_publication.meta or {}).get("config_snapshot") or {}) if target_publication else {}
            if not target_publication or not target_config_snapshot:
                validation_failures.append(asset_name)
                continue
            try:
                self._validate_asset_config(asset_name, target_config_snapshot)
            except ValueError:
                validation_failures.append(asset_name)
                continue
            rollback_targets[asset_name] = {
                "publication": target_publication,
                "config_snapshot": target_config_snapshot,
            }

        if stale_assets:
            request.status = "stale_request"
            request.meta = dict(request.meta or {})
            request.meta["stale_assets"] = stale_assets
            request.save(update_fields=["status", "meta", "updated_at"])
            raise ValueError("Rollback request is stale because the current published asset changed after proposal creation.")

        if validation_failures:
            request.status = "failed_validation"
            request.meta = dict(request.meta or {})
            request.meta["validation_failures"] = validation_failures
            request.save(update_fields=["status", "meta", "updated_at"])
            raise ValueError("Rollback request failed validation because a target snapshot could not be restored safely.")

        original_contents = {}
        try:
            for asset_name, rollback_target in rollback_targets.items():
                path = self._asset_path(asset_name)
                original_contents[asset_name] = path.read_text(encoding="utf-8")
                self._write_asset_snapshot(asset_name, rollback_target["config_snapshot"])
            self.config_service.reload()
            for asset_name in rollback_targets:
                self._load_asset(asset_name)
            asset_snapshots = self._build_asset_snapshots(assets=request.asset_types)
            publications = []
            for asset_name in request.asset_types:
                publication = self._ensure_asset_publication(
                    asset_name,
                    asset_snapshots[asset_name],
                    asset_snapshots,
                    publish_source="engineering_rollback_workflow",
                    request_context={
                        "request_id": request.request_id,
                        "requested_by": request.requested_by,
                        "proposal_source": request.proposal_source,
                        "reason": request.reason,
                        "notes": request.notes,
                        "executed_by": str(executed_by or "").strip(),
                        "action_type": "rollback",
                        "rollback_target_publication_id": rollback_targets[asset_name]["publication"].publication_id,
                    },
                )
                publications.append(publication)
        except Exception:
            for asset_name, contents in original_contents.items():
                self._asset_path(asset_name).write_text(contents, encoding="utf-8")
            self.config_service.reload()
            request.status = "failed_execution"
            request.meta = dict(request.meta or {})
            request.meta["execution_failure"] = "config_restore_reverted"
            request.save(update_fields=["status", "meta", "updated_at"])
            raise

        request.status = "rolled_back"
        request.executed_by = str(executed_by or "").strip()
        request.executed_at = timezone.now()
        request.published_publication_ids = [publication.publication_id for publication in publications]
        request.meta = dict(request.meta or {})
        request.meta["published_assets"] = {
            publication.asset_type: publication.publication_id for publication in publications
        }
        request.save(
            update_fields=[
                "status",
                "executed_by",
                "executed_at",
                "published_publication_ids",
                "meta",
                "updated_at",
            ]
        )
        return {
            "request": self._serialize_publish_request(request),
            "publications": [self._serialize_publication(publication) for publication in publications],
        }

    def _build_asset_snapshots(self, assets=None):
        asset_names = list(assets or self.GOVERNED_ASSETS)
        snapshots = {}
        for asset_name in asset_names:
            if asset_name not in self.GOVERNED_ASSETS:
                raise ValueError(f"Unsupported governed asset: {asset_name}")
            config = self._load_asset(asset_name)
            path = self._asset_path(asset_name)
            snapshots[asset_name] = {
                "config": config,
                "path": path,
                "version": str(config.get("version") or ""),
                "checksum": self._calculate_file_checksum(path),
            }
        return snapshots

    def _ensure_asset_publication(self, asset_name, snapshot, all_snapshots, publish_source=None, request_context=None):
        existing = (
            ProcurementConfigPublication.objects.filter(
                asset_type=asset_name,
                asset_version=snapshot["version"],
                file_checksum=snapshot["checksum"],
                status="published",
            )
            .order_by("-created_at", "-id")
            .first()
        )
        if existing:
            self._backfill_publication_snapshot(existing, snapshot=snapshot, governed_snapshots=all_snapshots)
            return existing

        previous = ProcurementConfigPublication.objects.filter(asset_type=asset_name).order_by("-created_at", "-id").first()
        if previous:
            ProcurementConfigPublication.objects.filter(asset_type=asset_name, status="published").update(
                status="superseded"
            )

        governed_versions = {
            governed_asset: asset_snapshot["version"] for governed_asset, asset_snapshot in all_snapshots.items()
        }
        request_context = dict(request_context or {})
        publication = ProcurementConfigPublication.objects.create(
            publication_id=str(uuid4()),
            asset_type=asset_name,
            asset_version=snapshot["version"],
            file_name=snapshot["path"].name,
            file_checksum=snapshot["checksum"],
            status="published",
            publish_source=publish_source or ("engineering_bootstrap" if previous is None else "engineering_config_sync"),
            rollback_target_publication_id=previous.publication_id if previous else "",
            rollback_target_version=previous.asset_version if previous else "",
            rollback_status="available" if previous else "not_available",
            meta={
                "hash_algorithm": "sha256",
                "publish_workflow": self.PUBLISH_WORKFLOW,
                "proposal_workflow": self.PROPOSAL_WORKFLOW,
                "rollback_mode": self.ROLLBACK_MODE,
                "governed_versions": governed_versions,
                "asset_file_path": str(snapshot["path"]),
                "config_snapshot": snapshot["config"],
                "request_context": request_context,
            },
        )
        return publication

    def _serialize_publication(self, publication):
        meta = dict(publication.meta or {})
        return {
            "publication_id": publication.publication_id,
            "asset_type": publication.asset_type,
            "asset_version": publication.asset_version,
            "file_name": publication.file_name,
            "file_checksum": publication.file_checksum,
            "status": publication.status,
            "publish_source": publication.publish_source,
            "published_at": publication.created_at,
            "updated_at": publication.updated_at,
            "rollback": {
                "status": publication.rollback_status,
                "supported": publication.rollback_status == "available",
                "target_publication_id": publication.rollback_target_publication_id,
                "target_version": publication.rollback_target_version,
                "mode": meta.get("rollback_mode") or self.ROLLBACK_MODE,
            },
            "meta": meta,
        }

    def _load_asset(self, asset_name):
        loader = {
            "rules": self.config_service.get_rules_config,
            "ranking": self.config_service.get_ranking_config,
            "policy": self.config_service.get_policy_config,
            "templates": self.config_service.get_template_config,
        }[asset_name]
        return loader()

    def _calculate_file_checksum(self, path):
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            digest.update(handle.read())
        return digest.hexdigest()

    def _serialize_publish_request(self, request):
        requested_snapshot = dict(request.requested_snapshot or {})
        return {
            "request_id": request.request_id,
            "action_type": request.action_type,
            "status": request.status,
            "asset_types": list(request.asset_types or []),
            "requested_by": request.requested_by,
            "proposal_source": request.proposal_source,
            "reason": request.reason,
            "notes": request.notes,
            "requested_snapshot": requested_snapshot,
            "published_publication_ids": list(request.published_publication_ids or []),
            "executed_by": request.executed_by,
            "executed_at": request.executed_at,
            "created_at": request.created_at,
            "updated_at": request.updated_at,
            "meta": dict(request.meta or {}),
        }

    def _require_engineering_publish_token(self, authorization_token):
        configured_token = str(os.getenv(self.ENGINEERING_PUBLISH_TOKEN_ENV, "") or "").strip()
        if not configured_token:
            raise PermissionError("Engineering publish token is not configured.")
        if str(authorization_token or "").strip() != configured_token:
            raise PermissionError("Engineering publish authorization failed.")

    def _get_current_publication(self, asset_name):
        return (
            ProcurementConfigPublication.objects.filter(asset_type=asset_name, status="published")
            .order_by("-created_at", "-id")
            .first()
        )

    def _backfill_publication_snapshot(self, publication, snapshot, governed_snapshots):
        if not publication:
            return
        meta = dict(publication.meta or {})
        changed = False
        if not meta.get("config_snapshot"):
            meta["config_snapshot"] = snapshot["config"]
            changed = True
        if not meta.get("asset_file_path"):
            meta["asset_file_path"] = str(snapshot["path"])
            changed = True
        if meta.get("publish_workflow") != self.PUBLISH_WORKFLOW:
            meta["publish_workflow"] = self.PUBLISH_WORKFLOW
            changed = True
        if meta.get("proposal_workflow") != self.PROPOSAL_WORKFLOW:
            meta["proposal_workflow"] = self.PROPOSAL_WORKFLOW
            changed = True
        if meta.get("rollback_mode") != self.ROLLBACK_MODE:
            meta["rollback_mode"] = self.ROLLBACK_MODE
            changed = True
        governed_versions = {
            governed_asset: asset_snapshot["version"] for governed_asset, asset_snapshot in governed_snapshots.items()
        }
        if meta.get("governed_versions") != governed_versions:
            meta["governed_versions"] = governed_versions
            changed = True
        if changed:
            publication.meta = meta
            publication.save(update_fields=["meta", "updated_at"])

    def _validate_asset_config(self, asset_name, config):
        validators = {
            "rules": self.config_service._validate_rules_config,
            "ranking": self.config_service._validate_ranking_config,
            "policy": self.config_service._validate_policy_config,
            "templates": self.config_service._validate_template_config,
        }
        validators[asset_name](config)

    def _asset_path(self, asset_name):
        return self.config_service.config_dir / self.config_service.CONFIG_FILES[asset_name]

    def _write_asset_snapshot(self, asset_name, config_snapshot):
        path = self._asset_path(asset_name)
        path.write_text(f"{json.dumps(config_snapshot, indent=2, ensure_ascii=False)}\n", encoding="utf-8")
