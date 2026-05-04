# import re

# from ...catalog.services.normalization import normalize_category, normalize_workloads
# from .llm_client import OptionalLLMClient


# class ProcurementMultiIntentService:
#     CONNECTOR_PATTERN = re.compile(
#         r"\s+(?:and also|as well as|along with|plus|&|and)\s+",
#         re.IGNORECASE,
#     )
#     PUNCTUATION_PATTERN = re.compile(r"[;\n]+")
#     INTENT_HINT_TOKENS = (
#         "laptop",
#         "laptops",
#         "desktop",
#         "desktops",
#         "server",
#         "servers",
#         "printer",
#         "printers",
#         "accessories",
#         "keyboard",
#         "keyboards",
#         "mouse",
#         "mice",
#         "headset",
#         "headsets",
#         "headphones",
#         "network",
#         "networking",
#         "router",
#         "switch",
#         "firewall",
#         "access point",
#         "wi-fi",
#         "wifi",
#         "developer",
#         "developers",
#         "design",
#         "designers",
#         "office",
#         "branch",
#         "retail",
#         "virtualization",
#         "vm",
#         "ai",
#         "analytics",
#     )
#     PRODUCT_INTENT_TOKENS = (
#         "laptop",
#         "laptops",
#         "desktop",
#         "desktops",
#         "server",
#         "servers",
#         "printer",
#         "printers",
#         "accessories",
#         "keyboard",
#         "keyboards",
#         "mouse",
#         "mice",
#         "headset",
#         "headsets",
#         "headphones",
#         "network",
#         "networking",
#         "router",
#         "switch",
#         "firewall",
#         "access point",
#         "wi-fi",
#         "wifi",
#     )
#     END_USER_WORKLOADS = {
#         "software_development",
#         "office_productivity",
#         "creative_design",
#     }
#     NETWORK_WORKLOADS = {"network_connectivity"}
#     END_USER_APPLICATION_SIGNALS = {
#         "developer_toolchain",
#         "design_toolchain",
#         "remote_collaboration",
#     }
#     NETWORK_APPLICATION_SIGNALS = {"branch_networking"}
#     END_USER_HINT_TOKENS = (
#         "developer",
#         "developers",
#         "designer",
#         "designers",
#         "staff",
#         "employees",
#         "users",
#         "workstations",
#         "systems",
#     )
#     NETWORK_HINT_TOKENS = (
#         "branch",
#         "secure branch access",
#         "network",
#         "networking",
#         "router",
#         "firewall",
#         "vpn",
#     )
#     SHARED_KEYS = {
#         "store_id",
#         "channel",
#         "currency",
#         "budget",
#         "budget_scope",
#         "growth_expectation",
#         "existing_infrastructure",
#         "preferred_manufacturers",
#         "blocked_manufacturers",
#         "preferred_sellers",
#         "blocked_sellers",
#         "performance_priority",
#         "portability_need",
#         "support_expectation",
#         "availability_need",
#         "require_returnable",
#         "timeline",
#         "industry",
#         "business_type",
#     }
#     CATEGORY_HINTS = {
#         "laptops": {
#             "laptop",
#             "laptops",
#             "notebook",
#             "notebooks",
#             "ultrabook",
#             "field team",
#             "sales reps",
#             "consultants",
#         },
#         "desktops": {
#             "desktop",
#             "desktops",
#             "pc",
#             "pcs",
#             "workstation",
#             "workstations",
#         },
#         "printers": {
#             "printer",
#             "printers",
#             "mfp",
#             "all in one",
#             "all-in-one",
#             "scanner printer",
#             "scan",
#             "scanner",
#             "copy",
#             "copier",
#         },
#         "networking": {
#             "network",
#             "networking",
#             "switch",
#             "switching",
#             "router",
#             "firewall",
#             "vpn",
#             "access point",
#             "wifi",
#             "wi-fi",
#         },
#         "servers": {
#             "server",
#             "servers",
#             "virtualization",
#             "vmware",
#             "hyper-v",
#             "proxmox",
#             "hypervisor",
#             "rack",
#         },
#         "accessories": {
#             "accessories",
#             "keyboard",
#             "mouse",
#             "headset",
#             "headsets",
#             "headphones",
#             "monitor",
#             "dock",
#         },
#     }

#     def __init__(self, extraction_service):
#         self.extraction_service = extraction_service
#         self.llm_client = getattr(extraction_service, "llm_client", None) or OptionalLLMClient()

#     def detect(self, payload, extracted_schema=None):
#         payload = dict(payload or {})
#         extracted_schema = dict(extracted_schema or {})
#         structured_groups = payload.get("intent_groups") or extracted_schema.get("intent_groups") or []
#         if structured_groups:
#             normalized = self.normalize_intent_groups(payload, extracted_schema, structured_groups)
#             if len(normalized) >= 2:
#                 return {
#                     "is_multi_intent": True,
#                     "split_source": "planner_intent_groups",
#                     "shared_budget_reused": payload.get("budget") is not None or extracted_schema.get("budget") is not None,
#                     "intents": normalized,
#                 }
#         chat_text = str(
#             payload.get("chat_text")
#             or payload.get("raw_chat")
#             or extracted_schema.get("raw_chat")
#             or ""
#         ).strip()
#         if not chat_text:
#             return {"is_multi_intent": False, "intents": []}

#         if self._is_category_choice_uncertainty(chat_text, extracted_schema):
#             return {"is_multi_intent": False, "intents": []}

#         force_category_split = self._should_force_category_split(chat_text, extracted_schema)
#         clauses = self._split_clauses(chat_text)
#         if len(clauses) < 2 and self._has_multiple_category_tracks(chat_text):
#             clauses = self._split_by_category_tracks(chat_text)
#         if len(clauses) < 2:
#             fallback_result = self._detect_mixed_workload_fallback(
#                 payload=payload,
#                 extracted_schema=extracted_schema,
#                 chat_text=chat_text,
#             )
#             if fallback_result:
#                 return fallback_result
#             llm_result = self._maybe_llm_detect(payload, extracted_schema, chat_text)
#             if llm_result:
#                 return llm_result
#             return {"is_multi_intent": False, "intents": []}

#         intents = []
#         seen_signatures = set()
#         for index, clause in enumerate(clauses, start=1):
#             clause_schema = self._extract_clause_schema(clause)
#             category = normalize_category(clause_schema.get("preferred_category"))
#             if category and not self._has_product_signal(clause):
#                 category = None
#                 clause_schema["preferred_category"] = None
#             if not category:
#                 inferred_category = self._dominant_category_hint(clause)
#                 if inferred_category:
#                     category = inferred_category
#                     clause_schema["preferred_category"] = inferred_category
#             workloads = normalize_workloads(clause_schema.get("workload_types"))
#             if not category and not workloads:
#                 continue
#             if not category and not self._has_product_signal(clause):
#                 continue
#             min_signals = 1 if force_category_split and category else 2
#             if self._signal_count(clause_schema, category, workloads) < min_signals:
#                 continue

#             signature = (
#                 category or "",
#                 tuple(sorted(workloads)),
#                 bool(clause_schema.get("quantity")),
#                 bool(clause_schema.get("team_size")),
#             )
#             if signature in seen_signatures:
#                 continue
#             seen_signatures.add(signature)

#             intents.append(
#                 {
#                     "group_id": f"intent-{index}",
#                     "label": self._intent_label(category, workloads, clause),
#                     "intent_text": clause,
#                     "category": category,
#                     "workloads": workloads,
#                     "extracted_schema": clause_schema,
#                     "payload": self._build_intent_payload(payload, extracted_schema, clause_schema, clause),
#                 }
#             )

#         intents = self._collapse_related_intents(intents)

#         if len(intents) < 2 or not self._has_distinct_signals(intents):
#             fallback_result = self._detect_mixed_workload_fallback(
#                 payload=payload,
#                 extracted_schema=extracted_schema,
#                 chat_text=chat_text,
#             )
#             if fallback_result:
#                 return fallback_result
#             llm_result = self._maybe_llm_detect(payload, extracted_schema, chat_text)
#             if llm_result:
#                 return llm_result
#             return {"is_multi_intent": False, "intents": []}

#         return {
#             "is_multi_intent": True,
#             "split_source": "chat_text",
#             "shared_budget_reused": payload.get("budget") is not None or extracted_schema.get("budget") is not None,
#             "intents": intents,
#         }

#     def normalize_intent_groups(self, payload, extracted_schema, intent_groups):
#         payload = dict(payload or {})
#         extracted_schema = dict(extracted_schema or {})
#         intents = []
#         for index, group in enumerate(list(intent_groups or []), start=1):
#             if not isinstance(group, dict):
#                 continue
#             category = normalize_category(group.get("preferred_category") or group.get("category"))
#             workloads = normalize_workloads(group.get("workloads") or group.get("workload_types"))
#             if not category and not workloads:
#                 continue
#             group_schema = dict(extracted_schema)
#             group_schema.update(dict(group))
#             intents.append(
#                 {
#                     "group_id": str(group.get("group_id") or f"intent-{index}"),
#                     "label": self._intent_label(category, workloads, group.get("label") or ""),
#                     "intent_text": str(group.get("intent_text") or group.get("label") or "").strip(),
#                     "category": category,
#                     "workloads": workloads,
#                     "extracted_schema": group_schema,
#                     "payload": self._build_intent_payload(payload, extracted_schema, group_schema, str(group.get("intent_text") or "")),
#                 }
#             )
#         return intents

#     def _maybe_llm_detect(self, payload, extracted_schema, chat_text):
#         chat_text = str(chat_text or "").strip()
#         if len(chat_text.split()) <= 15:
#             return None
#         if not self._has_intent_hint(chat_text):
#             return None
#         return self._llm_detect(payload, extracted_schema, chat_text)

#     def _llm_detect(self, payload, extracted_schema, chat_text):
#         if not self.llm_client or not self.llm_client.is_available():
#             return None
#         llm_result = self.llm_client.invoke_json(
#             "multi_intent_detect.txt",
#             {"chat_text": chat_text},
#             request_options={
#                 "timeout_sec": OptionalLLMClient.FAST_PATH_TIMEOUT_SEC,
#                 "max_tokens": 240,
#                 "reasoning_effort": "low",
#             },
#         )
#         intents = self._build_llm_intents(payload, extracted_schema, llm_result)
#         if len(intents) < 2 or not self._has_distinct_signals(intents):
#             return None
#         return {
#             "is_multi_intent": True,
#             "split_source": "llm_fallback",
#             "shared_budget_reused": payload.get("budget") is not None or extracted_schema.get("budget") is not None,
#             "intents": intents,
#         }

#     def _build_llm_intents(self, payload, extracted_schema, llm_result):
#         llm_result = dict(llm_result or {})
#         if not llm_result.get("is_multi_intent"):
#             return []
#         intents = []
#         seen_signatures = set()
#         for index, item in enumerate(list(llm_result.get("intents") or []), start=1):
#             clause = str((item or {}).get("intent_text") or "").strip(" ,.")
#             if not clause:
#                 continue
#             clause_schema = self._extract_clause_schema(clause)
#             category = normalize_category(clause_schema.get("preferred_category"))
#             hinted_category = normalize_category((item or {}).get("category"))
#             if category and not self._has_product_signal(clause):
#                 category = None
#                 clause_schema["preferred_category"] = None
#             if not category:
#                 inferred_category = self._dominant_category_hint(clause)
#                 if inferred_category:
#                     category = inferred_category
#                     clause_schema["preferred_category"] = inferred_category
#             if not category and hinted_category:
#                 category = hinted_category
#                 clause_schema["preferred_category"] = hinted_category
#             workloads = normalize_workloads(clause_schema.get("workload_types"))
#             hinted_workloads = normalize_workloads((item or {}).get("workloads"))
#             if not workloads and hinted_workloads:
#                 workloads = hinted_workloads
#                 clause_schema["workload_types"] = hinted_workloads
#             if not category and not workloads:
#                 continue
#             if not category and not self._has_product_signal(clause):
#                 continue
#             signature = (
#                 category or "",
#                 tuple(sorted(workloads)),
#                 bool(clause_schema.get("quantity")),
#                 bool(clause_schema.get("team_size")),
#             )
#             if signature in seen_signatures:
#                 continue
#             seen_signatures.add(signature)
#             intents.append(
#                 {
#                     "group_id": f"intent-{index}",
#                     "label": self._intent_label(category, workloads, clause),
#                     "intent_text": clause,
#                     "category": category,
#                     "workloads": workloads,
#                     "extracted_schema": clause_schema,
#                     "payload": self._build_intent_payload(payload, extracted_schema, clause_schema, clause),
#                 }
#             )
#         return self._collapse_related_intents(intents)

#     def _collapse_related_intents(self, intents):
#         collapsed = []
#         for intent in list(intents or []):
#             category = intent.get("category")
#             workloads = tuple(sorted(intent.get("workloads") or []))
#             merged = False
#             for existing in collapsed:
#                 existing_category = existing.get("category")
#                 existing_workloads = tuple(sorted(existing.get("workloads") or []))
#                 if category and existing_category and category == existing_category:
#                     merged = True
#                 elif (
#                     workloads
#                     and existing_workloads
#                     and workloads == existing_workloads
#                     and not (category and existing_category and category != existing_category)
#                 ):
#                     merged = True
#                 elif not category and existing_workloads and workloads and set(workloads).issubset(set(existing_workloads)):
#                     merged = True
#                 elif not existing_category and existing_workloads and workloads and set(existing_workloads).issubset(set(workloads)):
#                     merged = True

#                 if not merged:
#                     continue

#                 combined_text = " ".join(
#                     part for part in [existing.get("intent_text"), intent.get("intent_text")] if str(part or "").strip()
#                 ).strip()
#                 existing["intent_text"] = combined_text
#                 existing["label"] = self._intent_label(
#                     existing.get("category") or category,
#                     existing.get("workloads") or intent.get("workloads"),
#                     combined_text or existing.get("label"),
#                 )
#                 break
#             if not merged:
#                 collapsed.append(intent)
#         return collapsed

#     def _detect_mixed_workload_fallback(self, payload, extracted_schema, chat_text):
#         extracted_schema = dict(extracted_schema or {})
#         workloads = normalize_workloads(extracted_schema.get("workload_types"))
#         workload_set = set(workloads)
#         if not workload_set.intersection(self.END_USER_WORKLOADS):
#             return None
#         if not workload_set.intersection(self.NETWORK_WORKLOADS):
#             return None

#         application_signals = {
#             str(signal or "").strip().lower()
#             for signal in (extracted_schema.get("application_signals") or [])
#             if str(signal or "").strip()
#         }
#         capability_tags = {
#             str(tag or "").strip().lower()
#             for tag in (extracted_schema.get("capability_tags") or [])
#             if str(tag or "").strip()
#         }
#         lowered = str(chat_text or "").strip().lower()

#         has_end_user_signal = bool(application_signals.intersection(self.END_USER_APPLICATION_SIGNALS)) or any(
#             token in lowered for token in self.END_USER_HINT_TOKENS
#         )
#         has_network_signal = (
#             bool(application_signals.intersection(self.NETWORK_APPLICATION_SIGNALS))
#             or "branch_connectivity" in capability_tags
#             or any(token in lowered for token in self.NETWORK_HINT_TOKENS)
#         )
#         if not (has_end_user_signal and has_network_signal):
#             return None

#         shared_budget_reused = payload.get("budget") is not None or extracted_schema.get("budget") is not None
#         team_size = extracted_schema.get("team_size")
#         quantity = extracted_schema.get("quantity") or team_size
#         raw_signals = list(extracted_schema.get("application_signals") or [])
#         raw_tags = list(extracted_schema.get("capability_tags") or [])

#         end_user_schema = self._build_synthetic_schema(
#             extracted_schema=extracted_schema,
#             raw_chat="systems for developers",
#             preferred_category=None,
#             workloads=[workload for workload in workloads if workload in self.END_USER_WORKLOADS],
#             application_signals=[
#                 signal
#                 for signal in raw_signals
#                 if str(signal or "").strip().lower() in self.END_USER_APPLICATION_SIGNALS
#             ],
#             capability_tags=[
#                 tag
#                 for tag in raw_tags
#                 if str(tag or "").strip().lower() in {"local_compute", "high_ram", "always_on"}
#             ],
#             quantity=quantity,
#             purchase_scope="team_rollout",
#         )
#         network_schema = self._build_synthetic_schema(
#             extracted_schema=extracted_schema,
#             raw_chat="secure branch access",
#             preferred_category="networking",
#             workloads=[workload for workload in workloads if workload in self.NETWORK_WORKLOADS],
#             application_signals=[
#                 signal
#                 for signal in raw_signals
#                 if str(signal or "").strip().lower() in self.NETWORK_APPLICATION_SIGNALS
#             ],
#             capability_tags=[
#                 tag
#                 for tag in raw_tags
#                 if str(tag or "").strip().lower() in {"branch_connectivity", "always_on"}
#             ],
#             quantity=None,
#             purchase_scope="site_deployment",
#         )

#         intents = []
#         for index, clause_schema in enumerate((end_user_schema, network_schema), start=1):
#             category = normalize_category(clause_schema.get("preferred_category"))
#             intent_workloads = normalize_workloads(clause_schema.get("workload_types"))
#             clause = str(clause_schema.get("raw_chat") or "").strip()
#             intents.append(
#                 {
#                     "group_id": f"intent-{index}",
#                     "label": self._intent_label(category, intent_workloads, clause),
#                     "intent_text": clause,
#                     "category": category,
#                     "workloads": intent_workloads,
#                     "extracted_schema": clause_schema,
#                     "payload": self._build_intent_payload(payload, extracted_schema, clause_schema, clause),
#                 }
#             )

#         return {
#             "is_multi_intent": True,
#             "split_source": "mixed_workload_fallback",
#             "shared_budget_reused": shared_budget_reused,
#             "intents": intents,
#         }

#     def _build_synthetic_schema(
#         self,
#         extracted_schema,
#         raw_chat,
#         preferred_category,
#         workloads,
#         application_signals,
#         capability_tags,
#         quantity,
#         purchase_scope,
#     ):
#         schema = {
#             "raw_chat": raw_chat,
#             "preferred_category": normalize_category(preferred_category),
#             "workload_types": normalize_workloads(workloads),
#             "application_signals": list(application_signals or []),
#             "capability_tags": list(capability_tags or []),
#             "team_size": extracted_schema.get("team_size"),
#             "quantity": quantity,
#             "purchase_scope": purchase_scope,
#             "missing_fields": [],
#             "intake_confidence": 1.0,
#         }
#         return schema

#     def _split_clauses(self, chat_text):
#         text = str(chat_text or "").strip()
#         if not text:
#             return []

#         raw_parts = []
#         last_index = 0
#         for match in self.CONNECTOR_PATTERN.finditer(text):
#             left = text[last_index:match.start()].strip(" ,.")
#             right_preview = text[match.end(): match.end() + 120].strip()
#             right_clause = re.split(r"[.;\n]+", right_preview, maxsplit=1)[0].strip()
#             if left and (self._has_intent_hint(left) or self._has_intent_hint(right_clause)):
#                 raw_parts.append(left)
#                 last_index = match.end()

#         raw_parts.append(text[last_index:].strip(" ,."))
#         expanded = []
#         for clause in raw_parts:
#             if not clause:
#                 continue
#             punct_parts = [part.strip(" ,.") for part in self.PUNCTUATION_PATTERN.split(clause) if part.strip(" ,.")]
#             candidate_parts = punct_parts if punct_parts else [clause]
#             for part in candidate_parts:
#                 if not part:
#                     continue
#                 segmented = self._split_by_category_tracks(part)
#                 if segmented:
#                     expanded.extend(segmented)
#                 else:
#                     expanded.append(part)
#         return [clause for clause in expanded if clause]

#     def _split_by_category_tracks(self, text):
#         segments = []
#         for part in [segment.strip(" ,.") for segment in self.CONNECTOR_PATTERN.split(str(text or "")) if segment.strip(" ,.")]:
#             category_hits = self._category_hits(part)
#             if len(category_hits) <= 1:
#                 if self._has_intent_hint(part):
#                     segments.append(part)
#                 continue
#             slices = self._slice_part_by_category_hits(part, category_hits)
#             if slices:
#                 segments.extend(slices)
#             elif self._has_intent_hint(part):
#                 segments.append(part)
#         deduped = []
#         seen = set()
#         for segment in segments:
#             normalized = " ".join(str(segment or "").split()).strip()
#             if not normalized or normalized.lower() in seen:
#                 continue
#             seen.add(normalized.lower())
#             deduped.append(normalized)
#         return deduped

#     def _slice_part_by_category_hits(self, part, category_hits):
#         ordered_hits = sorted(category_hits, key=lambda item: item["start"])
#         slices = []
#         lead_text = part[: ordered_hits[0]["start"]].strip(" ,.")
#         for index, hit in enumerate(ordered_hits):
#             start = hit["start"]
#             end = ordered_hits[index + 1]["start"] if index + 1 < len(ordered_hits) else len(part)
#             chunk = part[start:end].strip(" ,.")
#             if lead_text and index == 0 and not chunk.lower().startswith(lead_text.lower()):
#                 chunk = f"{lead_text} {chunk}".strip()
#             if self._has_intent_hint(chunk):
#                 slices.append(chunk)
#         return slices

#     def _category_hits(self, text):
#         lowered = str(text or "").strip().lower()
#         hits = []
#         for category, tokens in self.CATEGORY_HINTS.items():
#             best_start = None
#             best_token = None
#             for token in tokens:
#                 pattern = r"(?<![a-z0-9])" + re.escape(token).replace(r"\ ", r"\s+") + r"(?![a-z0-9])"
#                 match = re.search(pattern, lowered)
#                 if match and (best_start is None or match.start() < best_start):
#                     best_start = match.start()
#                     best_token = token
#             if best_start is not None:
#                 hits.append({"category": category, "start": best_start, "token": best_token})
#         return hits

#     def _has_multiple_category_tracks(self, text):
#         categories = {item["category"] for item in self._category_hits(text)}
#         return len(categories) >= 2

#     def _is_category_choice_uncertainty(self, text, extracted_schema):
#         lowered = str(text or "").strip().lower()
#         if not lowered or not self._has_multiple_category_tracks(lowered):
#             return False
#         preferred_category = normalize_category(dict(extracted_schema or {}).get("preferred_category"))
#         if preferred_category and preferred_category != "not_sure" and "not sure" not in lowered and "not decided" not in lowered:
#             return False
#         uncertainty_tokens = (
#             "not sure",
#             "unsure",
#             "not decided",
#             "haven't decided",
#             "have not decided",
#             "can't decide",
#             "cannot decide",
#             "decide between",
#             "choose between",
#             "laptops or desktops",
#             "desktop or laptop",
#             "laptop or desktop",
#         )
#         return any(token in lowered for token in uncertainty_tokens)

#     def _dominant_category_hint(self, text):
#         hits = self._category_hits(text)
#         if not hits:
#             return None
#         ordered_hits = sorted(hits, key=lambda item: item["start"])
#         return ordered_hits[0]["category"]

#     def _should_force_category_split(self, chat_text, extracted_schema):
#         extracted_schema = dict(extracted_schema or {})
#         if normalize_category(extracted_schema.get("preferred_category")) != "not_sure":
#             return False
#         if not self._has_multiple_category_tracks(chat_text):
#             return False
#         workload_count = len(normalize_workloads(extracted_schema.get("workload_types")))
#         return workload_count >= 2 or self._has_multiple_category_tracks(chat_text)

#     def _has_intent_hint(self, text):
#         lowered = str(text or "").strip().lower()
#         if not lowered:
#             return False
#         window = lowered[:90]
#         return any(token in window for token in self.INTENT_HINT_TOKENS)

#     def _has_product_signal(self, text):
#         lowered = str(text or "").strip().lower()
#         if not lowered:
#             return False
#         window = lowered[:90]
#         return any(token in window for token in self.PRODUCT_INTENT_TOKENS)

#     def _extract_clause_schema(self, clause):
#         schema = self.extraction_service.extract(clause, context={})
#         schema = dict(schema or {})
#         schema["raw_chat"] = clause
#         schema["preferred_category"] = normalize_category(schema.get("preferred_category"))
#         schema["workload_types"] = normalize_workloads(schema.get("workload_types"))
#         schema["missing_fields"] = []
#         schema["intake_confidence"] = 1.0 if schema.get("preferred_category") or schema.get("workload_types") else 0.0
#         return schema

#     def _build_intent_payload(self, payload, extracted_schema, clause_schema, clause):
#         shared_payload = {}
#         for key in self.SHARED_KEYS:
#             if key in payload and payload.get(key) is not None:
#                 shared_payload[key] = payload.get(key)
#             elif key in extracted_schema and extracted_schema.get(key) is not None:
#                 shared_payload[key] = extracted_schema.get(key)
#         shared_payload["chat_text"] = clause
#         shared_payload["raw_chat"] = clause
#         shared_payload["extracted_schema"] = clause_schema
#         return self.extraction_service.build_procurement_payload(clause_schema, shared_payload)

#     def _intent_label(self, category, workloads, clause):
#         if category and workloads:
#             return f"{category.title()} - {workloads[0].replace('_', ' ').title()}"
#         if category:
#             return category.title()
#         if workloads:
#             return workloads[0].replace("_", " ").title()
#         return clause[:48]

#     def _has_distinct_signals(self, intents):
#         categories = {intent.get("category") for intent in intents if intent.get("category")}
#         workload_sets = {
#             tuple(sorted(intent.get("workloads") or []))
#             for intent in intents
#             if intent.get("workloads")
#         }
#         labels = {
#             str(intent.get("label") or "").strip().lower()
#             for intent in intents
#             if str(intent.get("label") or "").strip()
#         }
#         return len(categories) > 1 or len(workload_sets) > 1 or len(labels) > 1

#     def _signal_count(self, clause_schema, category, workloads):
#         clause_schema = dict(clause_schema or {})
#         return sum(
#             1
#             for signal in (
#                 bool(category),
#                 bool(workloads),
#                 bool(clause_schema.get("application_signals")),
#                 bool(clause_schema.get("quantity") or clause_schema.get("team_size")),
#                 clause_schema.get("budget") is not None,
#                 bool(clause_schema.get("requested_ram") or clause_schema.get("requested_storage")),
#             )
#             if signal
#         )




#########################################################################################################

# import re

# from ...catalog.services.normalization import normalize_category, normalize_workloads
# from .llm_client import OptionalLLMClient


# class ProcurementMultiIntentService:
#     CONNECTOR_PATTERN = re.compile(
#         r"\s+(?:and also|as well as|along with|plus|&|and)\s+",
#         re.IGNORECASE,
#     )
#     PUNCTUATION_PATTERN = re.compile(r"[;\n]+")
#     INTENT_HINT_TOKENS = (
#         "laptop",
#         "laptops",
#         "desktop",
#         "desktops",
#         "server",
#         "servers",
#         "printer",
#         "printers",
#         "accessories",
#         "keyboard",
#         "keyboards",
#         "mouse",
#         "mice",
#         "headset",
#         "headsets",
#         "headphones",
#         "network",
#         "networking",
#         "router",
#         "switch",
#         "firewall",
#         "access point",
#         "wi-fi",
#         "wifi",
#         "developer",
#         "developers",
#         "design",
#         "designers",
#         "office",
#         "branch",
#         "retail",
#         "virtualization",
#         "vm",
#         "ai",
#         "analytics",
#     )
#     PRODUCT_INTENT_TOKENS = (
#         "laptop",
#         "laptops",
#         "desktop",
#         "desktops",
#         "server",
#         "servers",
#         "printer",
#         "printers",
#         "accessories",
#         "keyboard",
#         "keyboards",
#         "mouse",
#         "mice",
#         "headset",
#         "headsets",
#         "headphones",
#         "network",
#         "networking",
#         "router",
#         "switch",
#         "firewall",
#         "access point",
#         "wi-fi",
#         "wifi",
#     )
#     END_USER_WORKLOADS = {
#         "software_development",
#         "office_productivity",
#         "creative_design",
#     }
#     NETWORK_WORKLOADS = {"network_connectivity"}
#     END_USER_APPLICATION_SIGNALS = {
#         "developer_toolchain",
#         "design_toolchain",
#         "remote_collaboration",
#     }
#     NETWORK_APPLICATION_SIGNALS = {"branch_networking"}
#     END_USER_HINT_TOKENS = (
#         "developer",
#         "developers",
#         "designer",
#         "designers",
#         "staff",
#         "employees",
#         "users",
#         "workstations",
#         "systems",
#     )
#     NETWORK_HINT_TOKENS = (
#         "branch",
#         "secure branch access",
#         "network",
#         "networking",
#         "router",
#         "firewall",
#         "vpn",
#     )
#     SHARED_KEYS = {
#         "store_id",
#         "channel",
#         "currency",
#         "budget",
#         "budget_scope",
#         "growth_expectation",
#         "existing_infrastructure",
#         "preferred_manufacturers",
#         "blocked_manufacturers",
#         "preferred_sellers",
#         "blocked_sellers",
#         "performance_priority",
#         "portability_need",
#         "support_expectation",
#         "availability_need",
#         "require_returnable",
#         "timeline",
#         "industry",
#         "business_type",
#     }
#     CATEGORY_HINTS = {
#         "laptops": {
#             "laptop",
#             "laptops",
#             "notebook",
#             "notebooks",
#             "ultrabook",
#             "field team",
#             "sales reps",
#             "consultants",
#         },
#         "desktops": {
#             "desktop",
#             "desktops",
#             "pc",
#             "pcs",
#             "workstation",
#             "workstations",
#         },
#         "printers": {
#             "printer",
#             "printers",
#             "mfp",
#             "all in one",
#             "all-in-one",
#             "scanner printer",
#             "scan",
#             "scanner",
#             "copy",
#             "copier",
#         },
#         "networking": {
#             "network",
#             "networking",
#             "switch",
#             "switching",
#             "router",
#             "firewall",
#             "vpn",
#             "access point",
#             "wifi",
#             "wi-fi",
#         },
#         "servers": {
#             "server",
#             "servers",
#             "virtualization",
#             "vmware",
#             "hyper-v",
#             "proxmox",
#             "hypervisor",
#             "rack",
#         },
#         "accessories": {
#             "accessories",
#             "keyboard",
#             "mouse",
#             "headset",
#             "headsets",
#             "headphones",
#             "monitor",
#             "dock",
#         },
#     }

#     def __init__(self, extraction_service):
#         self.extraction_service = extraction_service
#         self.llm_client = getattr(extraction_service, "llm_client", None) or OptionalLLMClient()

#     def detect(self, payload, extracted_schema=None):
#         payload = dict(payload or {})
#         extracted_schema = dict(extracted_schema or {})
#         structured_groups = payload.get("intent_groups") or extracted_schema.get("intent_groups") or []
#         if structured_groups:
#             normalized = self.normalize_intent_groups(payload, extracted_schema, structured_groups)
#             if len(normalized) >= 2:
#                 return {
#                     "is_multi_intent": True,
#                     "split_source": "planner_intent_groups",
#                     "shared_budget_reused": payload.get("budget") is not None or extracted_schema.get("budget") is not None,
#                     "intents": normalized,
#                 }
#         chat_text = str(
#             payload.get("chat_text")
#             or payload.get("raw_chat")
#             or extracted_schema.get("raw_chat")
#             or ""
#         ).strip()
#         if not chat_text:
#             return {"is_multi_intent": False, "intents": []}

#         if self._is_category_choice_uncertainty(chat_text, extracted_schema):
#             return {"is_multi_intent": False, "intents": []}

#         force_category_split = self._should_force_category_split(chat_text, extracted_schema)
#         clauses = self._split_clauses(chat_text)
#         if len(clauses) < 2 and self._has_multiple_category_tracks(chat_text):
#             clauses = self._split_by_category_tracks(chat_text)
#         if len(clauses) < 2:
#             fallback_result = self._detect_mixed_workload_fallback(
#                 payload=payload,
#                 extracted_schema=extracted_schema,
#                 chat_text=chat_text,
#             )
#             if fallback_result:
#                 return fallback_result
#             llm_result = self._maybe_llm_detect(payload, extracted_schema, chat_text)
#             if llm_result:
#                 return llm_result
#             return {"is_multi_intent": False, "intents": []}

#         intents = []
#         seen_signatures = set()
#         category_split_active = force_category_split or self._has_multiple_category_tracks(chat_text)
#         for index, clause in enumerate(clauses, start=1):
#             clause_schema = self._extract_clause_schema(clause)
#             category = normalize_category(clause_schema.get("preferred_category"))
#             if category and not self._has_product_signal(clause):
#                 category = None
#                 clause_schema["preferred_category"] = None
#             if not category:
#                 inferred_category = self._dominant_category_hint(clause)
#                 if inferred_category:
#                     category = inferred_category
#                     clause_schema["preferred_category"] = inferred_category
#             workloads = normalize_workloads(clause_schema.get("workload_types"))
#             if not category and not workloads:
#                 continue
#             if not category and not self._has_product_signal(clause):
#                 continue
#             min_signals = 1 if category_split_active and category else 2
#             if self._signal_count(clause_schema, category, workloads) < min_signals:
#                 continue

#             signature = (
#                 category or "",
#                 tuple(sorted(workloads)),
#                 bool(clause_schema.get("quantity")),
#                 bool(clause_schema.get("team_size")),
#             )
#             if signature in seen_signatures:
#                 continue
#             seen_signatures.add(signature)

#             intents.append(
#                 {
#                     "group_id": f"intent-{index}",
#                     "label": self._intent_label(category, workloads, clause),
#                     "intent_text": clause,
#                     "category": category,
#                     "workloads": workloads,
#                     "extracted_schema": clause_schema,
#                     "payload": self._build_intent_payload(payload, extracted_schema, clause_schema, clause),
#                 }
#             )

#         intents = self._collapse_related_intents(intents)

#         if len(intents) < 2 or not self._has_distinct_signals(intents):
#             fallback_result = self._detect_mixed_workload_fallback(
#                 payload=payload,
#                 extracted_schema=extracted_schema,
#                 chat_text=chat_text,
#             )
#             if fallback_result:
#                 return fallback_result
#             llm_result = self._maybe_llm_detect(payload, extracted_schema, chat_text)
#             if llm_result:
#                 return llm_result
#             return {"is_multi_intent": False, "intents": []}

#         return {
#             "is_multi_intent": True,
#             "split_source": "chat_text",
#             "shared_budget_reused": payload.get("budget") is not None or extracted_schema.get("budget") is not None,
#             "intents": intents,
#         }

#     def normalize_intent_groups(self, payload, extracted_schema, intent_groups):
#         payload = dict(payload or {})
#         extracted_schema = dict(extracted_schema or {})
#         intents = []
#         for index, group in enumerate(list(intent_groups or []), start=1):
#             if not isinstance(group, dict):
#                 continue
#             category = normalize_category(group.get("preferred_category") or group.get("category"))
#             workloads = normalize_workloads(group.get("workloads") or group.get("workload_types"))
#             if not category and not workloads:
#                 continue
#             group_schema = dict(extracted_schema)
#             group_schema.update(dict(group))
#             intents.append(
#                 {
#                     "group_id": str(group.get("group_id") or f"intent-{index}"),
#                     "label": self._intent_label(category, workloads, group.get("label") or ""),
#                     "intent_text": str(group.get("intent_text") or group.get("label") or "").strip(),
#                     "category": category,
#                     "workloads": workloads,
#                     "extracted_schema": group_schema,
#                     "payload": self._build_intent_payload(payload, extracted_schema, group_schema, str(group.get("intent_text") or "")),
#                 }
#             )
#         return intents

#     def _maybe_llm_detect(self, payload, extracted_schema, chat_text):
#         chat_text = str(chat_text or "").strip()
#         if len(chat_text.split()) <= 15:
#             return None
#         if not self._has_intent_hint(chat_text):
#             return None
#         return self._llm_detect(payload, extracted_schema, chat_text)

#     def _llm_detect(self, payload, extracted_schema, chat_text):
#         if not self.llm_client or not self.llm_client.is_available():
#             return None
#         llm_result = self.llm_client.invoke_json(
#             "multi_intent_detect.txt",
#             {"chat_text": chat_text},
#             request_options={
#                 "timeout_sec": OptionalLLMClient.FAST_PATH_TIMEOUT_SEC,
#                 "max_tokens": 240,
#                 "reasoning_effort": "low",
#             },
#         )
#         intents = self._build_llm_intents(payload, extracted_schema, llm_result)
#         if len(intents) < 2 or not self._has_distinct_signals(intents):
#             return None
#         return {
#             "is_multi_intent": True,
#             "split_source": "llm_fallback",
#             "shared_budget_reused": payload.get("budget") is not None or extracted_schema.get("budget") is not None,
#             "intents": intents,
#         }

#     def _build_llm_intents(self, payload, extracted_schema, llm_result):
#         llm_result = dict(llm_result or {})
#         if not llm_result.get("is_multi_intent"):
#             return []
#         intents = []
#         seen_signatures = set()
#         for index, item in enumerate(list(llm_result.get("intents") or []), start=1):
#             clause = str((item or {}).get("intent_text") or "").strip(" ,.")
#             if not clause:
#                 continue
#             clause_schema = self._extract_clause_schema(clause)
#             category = normalize_category(clause_schema.get("preferred_category"))
#             hinted_category = normalize_category((item or {}).get("category"))
#             if category and not self._has_product_signal(clause):
#                 category = None
#                 clause_schema["preferred_category"] = None
#             if not category:
#                 inferred_category = self._dominant_category_hint(clause)
#                 if inferred_category:
#                     category = inferred_category
#                     clause_schema["preferred_category"] = inferred_category
#             if not category and hinted_category:
#                 category = hinted_category
#                 clause_schema["preferred_category"] = hinted_category
#             workloads = normalize_workloads(clause_schema.get("workload_types"))
#             hinted_workloads = normalize_workloads((item or {}).get("workloads"))
#             if not workloads and hinted_workloads:
#                 workloads = hinted_workloads
#                 clause_schema["workload_types"] = hinted_workloads
#             if not category and not workloads:
#                 continue
#             if not category and not self._has_product_signal(clause):
#                 continue
#             signature = (
#                 category or "",
#                 tuple(sorted(workloads)),
#                 bool(clause_schema.get("quantity")),
#                 bool(clause_schema.get("team_size")),
#             )
#             if signature in seen_signatures:
#                 continue
#             seen_signatures.add(signature)
#             intents.append(
#                 {
#                     "group_id": f"intent-{index}",
#                     "label": self._intent_label(category, workloads, clause),
#                     "intent_text": clause,
#                     "category": category,
#                     "workloads": workloads,
#                     "extracted_schema": clause_schema,
#                     "payload": self._build_intent_payload(payload, extracted_schema, clause_schema, clause),
#                 }
#             )
#         return self._collapse_related_intents(intents)

#     def _collapse_related_intents(self, intents):
#         collapsed = []
#         for intent in list(intents or []):
#             category = intent.get("category")
#             workloads = tuple(sorted(intent.get("workloads") or []))
#             merged = False
#             for existing in collapsed:
#                 existing_category = existing.get("category")
#                 existing_workloads = tuple(sorted(existing.get("workloads") or []))
#                 if category and existing_category and category == existing_category:
#                     merged = True
#                 elif (
#                     workloads
#                     and existing_workloads
#                     and workloads == existing_workloads
#                     and not (category and existing_category and category != existing_category)
#                 ):
#                     merged = True
#                 elif not category and existing_workloads and workloads and set(workloads).issubset(set(existing_workloads)):
#                     merged = True
#                 elif not existing_category and existing_workloads and workloads and set(existing_workloads).issubset(set(workloads)):
#                     merged = True

#                 if not merged:
#                     continue

#                 combined_text = " ".join(
#                     part for part in [existing.get("intent_text"), intent.get("intent_text")] if str(part or "").strip()
#                 ).strip()
#                 existing["intent_text"] = combined_text
#                 existing["label"] = self._intent_label(
#                     existing.get("category") or category,
#                     existing.get("workloads") or intent.get("workloads"),
#                     combined_text or existing.get("label"),
#                 )
#                 break
#             if not merged:
#                 collapsed.append(intent)
#         return collapsed

#     def _detect_mixed_workload_fallback(self, payload, extracted_schema, chat_text):
#         extracted_schema = dict(extracted_schema or {})
#         workloads = normalize_workloads(extracted_schema.get("workload_types"))
#         workload_set = set(workloads)
#         if not workload_set.intersection(self.END_USER_WORKLOADS):
#             return None
#         if not workload_set.intersection(self.NETWORK_WORKLOADS):
#             return None

#         application_signals = {
#             str(signal or "").strip().lower()
#             for signal in (extracted_schema.get("application_signals") or [])
#             if str(signal or "").strip()
#         }
#         capability_tags = {
#             str(tag or "").strip().lower()
#             for tag in (extracted_schema.get("capability_tags") or [])
#             if str(tag or "").strip()
#         }
#         lowered = str(chat_text or "").strip().lower()

#         has_end_user_signal = bool(application_signals.intersection(self.END_USER_APPLICATION_SIGNALS)) or any(
#             token in lowered for token in self.END_USER_HINT_TOKENS
#         )
#         has_network_signal = (
#             bool(application_signals.intersection(self.NETWORK_APPLICATION_SIGNALS))
#             or "branch_connectivity" in capability_tags
#             or any(token in lowered for token in self.NETWORK_HINT_TOKENS)
#         )
#         if not (has_end_user_signal and has_network_signal):
#             return None

#         shared_budget_reused = payload.get("budget") is not None or extracted_schema.get("budget") is not None
#         team_size = extracted_schema.get("team_size")
#         quantity = extracted_schema.get("quantity") or team_size
#         raw_signals = list(extracted_schema.get("application_signals") or [])
#         raw_tags = list(extracted_schema.get("capability_tags") or [])

#         end_user_schema = self._build_synthetic_schema(
#             extracted_schema=extracted_schema,
#             raw_chat="systems for developers",
#             preferred_category=None,
#             workloads=[workload for workload in workloads if workload in self.END_USER_WORKLOADS],
#             application_signals=[
#                 signal
#                 for signal in raw_signals
#                 if str(signal or "").strip().lower() in self.END_USER_APPLICATION_SIGNALS
#             ],
#             capability_tags=[
#                 tag
#                 for tag in raw_tags
#                 if str(tag or "").strip().lower() in {"local_compute", "high_ram", "always_on"}
#             ],
#             quantity=quantity,
#             purchase_scope="team_rollout",
#         )
#         network_schema = self._build_synthetic_schema(
#             extracted_schema=extracted_schema,
#             raw_chat="secure branch access",
#             preferred_category="networking",
#             workloads=[workload for workload in workloads if workload in self.NETWORK_WORKLOADS],
#             application_signals=[
#                 signal
#                 for signal in raw_signals
#                 if str(signal or "").strip().lower() in self.NETWORK_APPLICATION_SIGNALS
#             ],
#             capability_tags=[
#                 tag
#                 for tag in raw_tags
#                 if str(tag or "").strip().lower() in {"branch_connectivity", "always_on"}
#             ],
#             quantity=None,
#             purchase_scope="site_deployment",
#         )

#         intents = []
#         for index, clause_schema in enumerate((end_user_schema, network_schema), start=1):
#             category = normalize_category(clause_schema.get("preferred_category"))
#             intent_workloads = normalize_workloads(clause_schema.get("workload_types"))
#             clause = str(clause_schema.get("raw_chat") or "").strip()
#             intents.append(
#                 {
#                     "group_id": f"intent-{index}",
#                     "label": self._intent_label(category, intent_workloads, clause),
#                     "intent_text": clause,
#                     "category": category,
#                     "workloads": intent_workloads,
#                     "extracted_schema": clause_schema,
#                     "payload": self._build_intent_payload(payload, extracted_schema, clause_schema, clause),
#                 }
#             )

#         return {
#             "is_multi_intent": True,
#             "split_source": "mixed_workload_fallback",
#             "shared_budget_reused": shared_budget_reused,
#             "intents": intents,
#         }

#     def _build_synthetic_schema(
#         self,
#         extracted_schema,
#         raw_chat,
#         preferred_category,
#         workloads,
#         application_signals,
#         capability_tags,
#         quantity,
#         purchase_scope,
#     ):
#         schema = {
#             "raw_chat": raw_chat,
#             "preferred_category": normalize_category(preferred_category),
#             "workload_types": normalize_workloads(workloads),
#             "application_signals": list(application_signals or []),
#             "capability_tags": list(capability_tags or []),
#             "team_size": extracted_schema.get("team_size"),
#             "quantity": quantity,
#             "purchase_scope": purchase_scope,
#             "missing_fields": [],
#             "intake_confidence": 1.0,
#         }
#         return schema

#     def _split_clauses(self, chat_text):
#         text = str(chat_text or "").strip()
#         if not text:
#             return []

#         raw_parts = []
#         last_index = 0
#         for match in self.CONNECTOR_PATTERN.finditer(text):
#             left = text[last_index:match.start()].strip(" ,.")
#             right_preview = text[match.end(): match.end() + 120].strip()
#             right_clause = re.split(r"[.;\n]+", right_preview, maxsplit=1)[0].strip()
#             if left and (self._has_intent_hint(left) or self._has_intent_hint(right_clause)):
#                 raw_parts.append(left)
#                 last_index = match.end()

#         raw_parts.append(text[last_index:].strip(" ,."))
#         expanded = []
#         for clause in raw_parts:
#             if not clause:
#                 continue
#             punct_parts = [part.strip(" ,.") for part in self.PUNCTUATION_PATTERN.split(clause) if part.strip(" ,.")]
#             candidate_parts = punct_parts if punct_parts else [clause]
#             for part in candidate_parts:
#                 if not part:
#                     continue
#                 segmented = self._split_by_category_tracks(part)
#                 if segmented:
#                     expanded.extend(segmented)
#                 else:
#                     expanded.append(part)
#         return [clause for clause in expanded if clause]

#     def _split_by_category_tracks(self, text):
#         segments = []
#         for part in [segment.strip(" ,.") for segment in self.CONNECTOR_PATTERN.split(str(text or "")) if segment.strip(" ,.")]:
#             category_hits = self._category_hits(part)
#             if len(category_hits) <= 1:
#                 if self._has_intent_hint(part):
#                     segments.append(part)
#                 continue
#             slices = self._slice_part_by_category_hits(part, category_hits)
#             if slices:
#                 segments.extend(slices)
#             elif self._has_intent_hint(part):
#                 segments.append(part)
#         deduped = []
#         seen = set()
#         for segment in segments:
#             normalized = " ".join(str(segment or "").split()).strip()
#             if not normalized or normalized.lower() in seen:
#                 continue
#             seen.add(normalized.lower())
#             deduped.append(normalized)
#         return deduped

#     def _slice_part_by_category_hits(self, part, category_hits):
#         ordered_hits = sorted(category_hits, key=lambda item: item["start"])
#         slices = []
#         lead_text = part[: ordered_hits[0]["start"]].strip(" ,.")
#         for index, hit in enumerate(ordered_hits):
#             start = hit["start"]
#             end = ordered_hits[index + 1]["start"] if index + 1 < len(ordered_hits) else len(part)
#             chunk = part[start:end].strip(" ,.")
#             if lead_text and index == 0 and not chunk.lower().startswith(lead_text.lower()):
#                 chunk = f"{lead_text} {chunk}".strip()
#             if self._has_intent_hint(chunk):
#                 slices.append(chunk)
#         return slices

#     def _category_hits(self, text):
#         lowered = str(text or "").strip().lower()
#         hits = []
#         for category, tokens in self.CATEGORY_HINTS.items():
#             best_start = None
#             best_token = None
#             for token in tokens:
#                 pattern = r"(?<![a-z0-9])" + re.escape(token).replace(r"\ ", r"\s+") + r"(?![a-z0-9])"
#                 match = re.search(pattern, lowered)
#                 if match and (best_start is None or match.start() < best_start):
#                     best_start = match.start()
#                     best_token = token
#             if best_start is not None:
#                 hits.append({"category": category, "start": best_start, "token": best_token})
#         return hits

#     def _has_multiple_category_tracks(self, text):
#         categories = {item["category"] for item in self._category_hits(text)}
#         return len(categories) >= 2

#     def _is_category_choice_uncertainty(self, text, extracted_schema):
#         lowered = str(text or "").strip().lower()
#         if not lowered or not self._has_multiple_category_tracks(lowered):
#             return False
#         preferred_category = normalize_category(dict(extracted_schema or {}).get("preferred_category"))
#         if preferred_category and preferred_category != "not_sure" and "not sure" not in lowered and "not decided" not in lowered:
#             return False
#         uncertainty_tokens = (
#             "not sure",
#             "unsure",
#             "not decided",
#             "haven't decided",
#             "have not decided",
#             "can't decide",
#             "cannot decide",
#             "decide between",
#             "choose between",
#             "laptops or desktops",
#             "desktop or laptop",
#             "laptop or desktop",
#         )
#         return any(token in lowered for token in uncertainty_tokens)

#     def _dominant_category_hint(self, text):
#         hits = self._category_hits(text)
#         if not hits:
#             return None
#         ordered_hits = sorted(hits, key=lambda item: item["start"])
#         return ordered_hits[0]["category"]

#     def _should_force_category_split(self, chat_text, extracted_schema):
#         extracted_schema = dict(extracted_schema or {})
#         if normalize_category(extracted_schema.get("preferred_category")) != "not_sure":
#             return False
#         if not self._has_multiple_category_tracks(chat_text):
#             return False
#         workload_count = len(normalize_workloads(extracted_schema.get("workload_types")))
#         return workload_count >= 2 or self._has_multiple_category_tracks(chat_text)

#     def _has_intent_hint(self, text):
#         lowered = str(text or "").strip().lower()
#         if not lowered:
#             return False
#         window = lowered[:90]
#         return any(token in window for token in self.INTENT_HINT_TOKENS)

#     def _has_product_signal(self, text):
#         lowered = str(text or "").strip().lower()
#         if not lowered:
#             return False
#         window = lowered[:90]
#         return any(token in window for token in self.PRODUCT_INTENT_TOKENS)

#     def _extract_clause_schema(self, clause):
#         schema = self.extraction_service.extract(clause, context={})
#         schema = dict(schema or {})
#         schema["raw_chat"] = clause
#         schema["preferred_category"] = normalize_category(schema.get("preferred_category"))
#         if not schema.get("preferred_category"):
#             hinted_category = self._dominant_category_hint(clause)
#             if hinted_category:
#                 schema["preferred_category"] = hinted_category
#         schema["workload_types"] = normalize_workloads(schema.get("workload_types"))
#         if not schema.get("workload_types") and schema.get("preferred_category") == "printers":
#             schema["workload_types"] = ["document_output"]
#         elif not schema.get("workload_types") and schema.get("preferred_category") == "networking":
#             schema["workload_types"] = ["network_connectivity"]
#         schema["missing_fields"] = []
#         schema["intake_confidence"] = 1.0 if schema.get("preferred_category") or schema.get("workload_types") else 0.0
#         return schema

#     def _build_intent_payload(self, payload, extracted_schema, clause_schema, clause):
#         shared_payload = {}
#         for key in self.SHARED_KEYS:
#             if key in payload and payload.get(key) is not None:
#                 shared_payload[key] = payload.get(key)
#             elif key in extracted_schema and extracted_schema.get(key) is not None:
#                 shared_payload[key] = extracted_schema.get(key)
#         shared_payload["chat_text"] = clause
#         shared_payload["raw_chat"] = clause
#         shared_payload["extracted_schema"] = clause_schema
#         return self.extraction_service.build_procurement_payload(clause_schema, shared_payload)

#     def _intent_label(self, category, workloads, clause):
#         if category and workloads:
#             return f"{category.title()} - {workloads[0].replace('_', ' ').title()}"
#         if category:
#             return category.title()
#         if workloads:
#             return workloads[0].replace("_", " ").title()
#         return clause[:48]

#     def _has_distinct_signals(self, intents):
#         categories = {intent.get("category") for intent in intents if intent.get("category")}
#         workload_sets = {
#             tuple(sorted(intent.get("workloads") or []))
#             for intent in intents
#             if intent.get("workloads")
#         }
#         labels = {
#             str(intent.get("label") or "").strip().lower()
#             for intent in intents
#             if str(intent.get("label") or "").strip()
#         }
#         return len(categories) > 1 or len(workload_sets) > 1 or len(labels) > 1

#     def _signal_count(self, clause_schema, category, workloads):
#         clause_schema = dict(clause_schema or {})
#         return sum(
#             1
#             for signal in (
#                 bool(category),
#                 bool(workloads),
#                 bool(clause_schema.get("application_signals")),
#                 bool(clause_schema.get("quantity") or clause_schema.get("team_size")),
#                 clause_schema.get("budget") is not None,
#                 bool(clause_schema.get("requested_ram") or clause_schema.get("requested_storage")),
#             )
#             if signal
#         )






import re

from ...catalog.services.normalization import normalize_categories, normalize_category, normalize_workloads
from .llm_client import OptionalLLMClient


class ProcurementMultiIntentService:
    CONNECTOR_PATTERN = re.compile(
        r"\s+(?:and also|as well as|along with|plus|&|and)\s+",
        re.IGNORECASE,
    )
    PUNCTUATION_PATTERN = re.compile(r"[;\n]+")
    INTENT_HINT_TOKENS = (
        "laptop",
        "laptops",
        "desktop",
        "desktops",
        "server",
        "servers",
        "printer",
        "printers",
        "accessories",
        "keyboard",
        "keyboards",
        "mouse",
        "mice",
        "headset",
        "headsets",
        "headphones",
        "network",
        "networking",
        "router",
        "switch",
        "firewall",
        "access point",
        "wi-fi",
        "wifi",
        "developer",
        "developers",
        "design",
        "designers",
        "office",
        "branch",
        "retail",
        "virtualization",
        "vm",
        "ai",
        "analytics",
    )
    PRODUCT_INTENT_TOKENS = (
        "laptop",
        "laptops",
        "desktop",
        "desktops",
        "server",
        "servers",
        "printer",
        "printers",
        "accessories",
        "keyboard",
        "keyboards",
        "mouse",
        "mice",
        "headset",
        "headsets",
        "headphones",
        "network",
        "networking",
        "router",
        "switch",
        "firewall",
        "access point",
        "wi-fi",
        "wifi",
    )
    END_USER_WORKLOADS = {
        "software_development",
        "office_productivity",
        "creative_design",
    }
    NETWORK_WORKLOADS = {"network_connectivity"}
    END_USER_APPLICATION_SIGNALS = {
        "developer_toolchain",
        "design_toolchain",
        "remote_collaboration",
    }
    NETWORK_APPLICATION_SIGNALS = {"branch_networking"}
    END_USER_HINT_TOKENS = (
        "developer",
        "developers",
        "designer",
        "designers",
        "staff",
        "employees",
        "users",
        "workstations",
        "systems",
    )
    NETWORK_HINT_TOKENS = (
        "branch",
        "secure branch access",
        "network",
        "networking",
        "router",
        "firewall",
        "vpn",
    )
    SHARED_KEYS = {
        "store_id",
        "channel",
        "currency",
        "budget",
        "budget_scope",
        "growth_expectation",
        "existing_infrastructure",
        "preferred_manufacturers",
        "blocked_manufacturers",
        "preferred_sellers",
        "blocked_sellers",
        "performance_priority",
        "portability_need",
        "support_expectation",
        "availability_need",
        "require_returnable",
        "timeline",
        "industry",
        "business_type",
    }
    CATEGORY_HINTS = {
        "laptops": {
            "laptop",
            "laptops",
            "notebook",
            "notebooks",
            "ultrabook",
            "field team",
            "sales reps",
            "consultants",
        },
        "desktops": {
            "desktop",
            "desktops",
            "pc",
            "pcs",
            "workstation",
            "workstations",
        },
        "printers": {
            "printer",
            "printers",
            "mfp",
            "all in one",
            "all-in-one",
            "scanner printer",
            "scan",
            "scanner",
            "copy",
            "copier",
        },
        "networking": {
            "network",
            "networking",
            "switch",
            "switching",
            "router",
            "firewall",
            "vpn",
            "access point",
            "wifi",
            "wi-fi",
        },
        "servers": {
            "server",
            "servers",
            "virtualization",
            "vmware",
            "hyper-v",
            "proxmox",
            "hypervisor",
            "rack",
        },
        "accessories": {
            "accessories",
            "keyboard",
            "mouse",
            "headset",
            "headsets",
            "headphones",
            "monitor",
            "dock",
        },
    }

    def __init__(self, extraction_service):
        self.extraction_service = extraction_service
        self.llm_client = getattr(extraction_service, "llm_client", None) or OptionalLLMClient()

    def detect(self, payload, extracted_schema=None):
        payload = dict(payload or {})
        extracted_schema = dict(extracted_schema or {})
        structured_groups = payload.get("intent_groups") or extracted_schema.get("intent_groups") or []
        if structured_groups:
            normalized = self.normalize_intent_groups(payload, extracted_schema, structured_groups)
            if len(normalized) >= 2:
                return {
                    "is_multi_intent": True,
                    "split_source": "planner_intent_groups",
                    "shared_budget_reused": payload.get("budget") is not None or extracted_schema.get("budget") is not None,
                    "intents": normalized,
                }

        explicit_category_result = self._synthesize_from_explicit_categories(payload, extracted_schema)
        chat_text = str(
            payload.get("chat_text")
            or payload.get("raw_chat")
            or extracted_schema.get("raw_chat")
            or ""
        ).strip()
        if not chat_text:
            return explicit_category_result or {"is_multi_intent": False, "intents": []}

        if self._is_category_choice_uncertainty(chat_text, extracted_schema):
            return {"is_multi_intent": False, "intents": []}

        force_category_split = self._should_force_category_split(chat_text, extracted_schema)
        clauses = self._split_clauses(chat_text)
        if len(clauses) < 2 and self._has_multiple_category_tracks(chat_text):
            clauses = self._split_by_category_tracks(chat_text)
        if len(clauses) < 2:
            fallback_result = self._detect_mixed_workload_fallback(
                payload=payload,
                extracted_schema=extracted_schema,
                chat_text=chat_text,
            )
            if fallback_result:
                return fallback_result
            if explicit_category_result:
                return explicit_category_result
            llm_result = self._maybe_llm_detect(payload, extracted_schema, chat_text)
            if llm_result:
                return llm_result
            return {"is_multi_intent": False, "intents": []}

        intents = []
        seen_signatures = set()
        category_split_active = force_category_split or self._has_multiple_category_tracks(chat_text)
        for index, clause in enumerate(clauses, start=1):
            clause_schema = self._extract_clause_schema(clause)
            category = normalize_category(clause_schema.get("preferred_category"))
            if category and not self._has_product_signal(clause):
                category = None
                clause_schema["preferred_category"] = None
            if not category:
                inferred_category = self._dominant_category_hint(clause)
                if inferred_category:
                    category = inferred_category
                    clause_schema["preferred_category"] = inferred_category
            workloads = normalize_workloads(clause_schema.get("workload_types"))
            if not category and not workloads:
                continue
            if not category and not self._has_product_signal(clause):
                continue
            min_signals = 1 if category_split_active and category else 2
            if self._signal_count(clause_schema, category, workloads) < min_signals:
                continue

            signature = (
                category or "",
                tuple(sorted(workloads)),
                bool(clause_schema.get("quantity")),
                bool(clause_schema.get("team_size")),
            )
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)

            intents.append(
                {
                    "group_id": f"intent-{index}",
                    "label": self._intent_label(category, workloads, clause),
                    "intent_text": clause,
                    "category": category,
                    "workloads": workloads,
                    "extracted_schema": clause_schema,
                    "payload": self._build_intent_payload(payload, extracted_schema, clause_schema, clause),
                }
            )

        intents = self._collapse_related_intents(intents)

        if len(intents) < 2 or not self._has_distinct_signals(intents):
            fallback_result = self._detect_mixed_workload_fallback(
                payload=payload,
                extracted_schema=extracted_schema,
                chat_text=chat_text,
            )
            if fallback_result:
                return fallback_result
            llm_result = self._maybe_llm_detect(payload, extracted_schema, chat_text)
            if llm_result:
                return llm_result
            return {"is_multi_intent": False, "intents": []}

        return {
            "is_multi_intent": True,
            "split_source": "chat_text",
            "shared_budget_reused": payload.get("budget") is not None or extracted_schema.get("budget") is not None,
            "intents": intents,
        }

    def normalize_intent_groups(self, payload, extracted_schema, intent_groups):
        payload = dict(payload or {})
        extracted_schema = dict(extracted_schema or {})
        intents = []
        for index, group in enumerate(list(intent_groups or []), start=1):
            if not isinstance(group, dict):
                continue
            category = normalize_category(group.get("preferred_category") or group.get("category"))
            workloads = normalize_workloads(group.get("workloads") or group.get("workload_types"))
            if not category and not workloads:
                continue
            group_schema = dict(extracted_schema)
            group_schema.update(dict(group))
            intents.append(
                {
                    "group_id": str(group.get("group_id") or f"intent-{index}"),
                    "label": self._intent_label(category, workloads, group.get("label") or ""),
                    "intent_text": str(group.get("intent_text") or group.get("label") or "").strip(),
                    "category": category,
                    "workloads": workloads,
                    "extracted_schema": group_schema,
                    "payload": self._build_intent_payload(payload, extracted_schema, group_schema, str(group.get("intent_text") or "")),
                }
            )
        return intents

    def _synthesize_from_explicit_categories(self, payload, extracted_schema):
        payload = dict(payload or {})
        extracted_schema = dict(extracted_schema or {})
        preferred_categories = normalize_categories(
            payload.get("preferred_categories")
            or extracted_schema.get("preferred_categories")
            or []
        )
        direct_category = normalize_category(payload.get("preferred_category") or extracted_schema.get("preferred_category"))
        if direct_category and direct_category != "not_sure" and direct_category not in preferred_categories:
            preferred_categories.insert(0, direct_category)
        preferred_categories = [category for category in preferred_categories if category and category != "not_sure"]
        if len(preferred_categories) < 2:
            return None

        base_workloads = normalize_workloads(
            extracted_schema.get("workload_types")
            or extracted_schema.get("workloads")
            or payload.get("workload_types")
            or payload.get("workloads")
            or []
        )
        application_signals = [
            signal for signal in list(extracted_schema.get("application_signals") or payload.get("application_signals") or [])
            if str(signal or "").strip()
        ]
        capability_tags = [
            tag for tag in list(extracted_schema.get("capability_tags") or payload.get("capability_tags") or [])
            if str(tag or "").strip()
        ]
        shared_budget_reused = payload.get("budget") is not None or extracted_schema.get("budget") is not None

        intents = []
        for index, category in enumerate(preferred_categories, start=1):
            clause_schema = dict(extracted_schema)
            clause_schema["preferred_category"] = category
            clause_schema["preferred_categories"] = [category]
            clause_schema["raw_chat"] = str(
                extracted_schema.get("raw_chat")
                or payload.get("raw_chat")
                or payload.get("chat_text")
                or category
            ).strip() or category
            clause_workloads = self._workloads_for_category_group(category, base_workloads)
            if clause_workloads:
                clause_schema["workload_types"] = clause_workloads
            else:
                clause_schema["workload_types"] = []
            clause_schema["application_signals"] = self._application_signals_for_category_group(category, application_signals)
            clause_schema["capability_tags"] = self._capability_tags_for_category_group(category, capability_tags)
            clause_text = clause_schema.get("raw_chat") or category
            intents.append(
                {
                    "group_id": f"intent-{index}",
                    "label": self._intent_label(category, clause_workloads, clause_text),
                    "intent_text": clause_text,
                    "category": category,
                    "workloads": clause_workloads,
                    "extracted_schema": clause_schema,
                    "payload": self._build_intent_payload(payload, extracted_schema, clause_schema, clause_text),
                }
            )

        intents = self._collapse_related_intents(intents)
        if len(intents) < 2 or not self._has_distinct_signals(intents):
            return None
        return {
            "is_multi_intent": True,
            "split_source": "explicit_categories",
            "shared_budget_reused": shared_budget_reused,
            "intents": intents,
        }

    def _workloads_for_category_group(self, category, workloads):
        category = normalize_category(category)
        workloads = normalize_workloads(workloads)
        if not category:
            return workloads
        mapping = {
            "laptops": {"software_development", "office_productivity", "creative_design"},
            "desktops": {"software_development", "office_productivity", "creative_design"},
            "servers": {"virtualization", "analytics_inference", "ai_compute"},
            "networking": {"network_connectivity"},
            "printers": {"document_output"},
            "accessories": {"peripheral_accessories"},
        }
        allowed = mapping.get(category)
        if not allowed:
            return workloads
        return [workload for workload in workloads if workload in allowed]

    def _application_signals_for_category_group(self, category, application_signals):
        category = normalize_category(category)
        signals = [str(signal or "").strip() for signal in list(application_signals or []) if str(signal or "").strip()]
        lowered = {signal.lower() for signal in signals}
        mapping = {
            "laptops": {"developer_toolchain", "design_toolchain", "business_apps", "remote_collaboration", "video_postproduction"},
            "desktops": {"developer_toolchain", "design_toolchain", "business_apps", "remote_collaboration", "video_postproduction"},
            "servers": {"virtualization_platform", "model_training", "analytics_stack"},
            "networking": {"branch_networking", "secure_connectivity"},
            "printers": {"document_output"},
            "accessories": {"peripheral_accessories"},
        }
        allowed = mapping.get(category)
        if not allowed:
            return signals
        return [signal for signal in signals if signal.lower() in allowed]

    def _capability_tags_for_category_group(self, category, capability_tags):
        category = normalize_category(category)
        tags = [str(tag or "").strip() for tag in list(capability_tags or []) if str(tag or "").strip()]
        lowered = {tag.lower() for tag in tags}
        mapping = {
            "laptops": {"portable", "display_sensitive", "gpu_needed", "storage_heavy", "high_ram", "always_on"},
            "desktops": {"gpu_needed", "storage_heavy", "high_ram", "always_on"},
            "servers": {"virtualization_ready", "high_availability", "always_on"},
            "networking": {"branch_connectivity", "always_on"},
            "printers": {"document_output"},
            "accessories": {"peripheral_accessories"},
        }
        allowed = mapping.get(category)
        if not allowed:
            return tags
        return [tag for tag in tags if tag.lower() in allowed]

    def _maybe_llm_detect(self, payload, extracted_schema, chat_text):
        chat_text = str(chat_text or "").strip()
        if len(chat_text.split()) <= 15:
            return None
        if not self._has_intent_hint(chat_text):
            return None
        return self._llm_detect(payload, extracted_schema, chat_text)

    def _llm_detect(self, payload, extracted_schema, chat_text):
        if not self.llm_client or not self.llm_client.is_available():
            return None
        llm_result = self.llm_client.invoke_json(
            "multi_intent_detect.txt",
            {"chat_text": chat_text},
            request_options={
                "timeout_sec": OptionalLLMClient.FAST_PATH_TIMEOUT_SEC,
                "max_tokens": 240,
                "reasoning_effort": "low",
            },
        )
        intents = self._build_llm_intents(payload, extracted_schema, llm_result)
        if len(intents) < 2 or not self._has_distinct_signals(intents):
            return None
        return {
            "is_multi_intent": True,
            "split_source": "llm_fallback",
            "shared_budget_reused": payload.get("budget") is not None or extracted_schema.get("budget") is not None,
            "intents": intents,
        }

    def _build_llm_intents(self, payload, extracted_schema, llm_result):
        llm_result = dict(llm_result or {})
        if not llm_result.get("is_multi_intent"):
            return []
        intents = []
        seen_signatures = set()
        for index, item in enumerate(list(llm_result.get("intents") or []), start=1):
            clause = str((item or {}).get("intent_text") or "").strip(" ,.")
            if not clause:
                continue
            clause_schema = self._extract_clause_schema(clause)
            category = normalize_category(clause_schema.get("preferred_category"))
            hinted_category = normalize_category((item or {}).get("category"))
            if category and not self._has_product_signal(clause):
                category = None
                clause_schema["preferred_category"] = None
            if not category:
                inferred_category = self._dominant_category_hint(clause)
                if inferred_category:
                    category = inferred_category
                    clause_schema["preferred_category"] = inferred_category
            if not category and hinted_category:
                category = hinted_category
                clause_schema["preferred_category"] = hinted_category
            workloads = normalize_workloads(clause_schema.get("workload_types"))
            hinted_workloads = normalize_workloads((item or {}).get("workloads"))
            if not workloads and hinted_workloads:
                workloads = hinted_workloads
                clause_schema["workload_types"] = hinted_workloads
            if not category and not workloads:
                continue
            if not category and not self._has_product_signal(clause):
                continue
            signature = (
                category or "",
                tuple(sorted(workloads)),
                bool(clause_schema.get("quantity")),
                bool(clause_schema.get("team_size")),
            )
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)
            intents.append(
                {
                    "group_id": f"intent-{index}",
                    "label": self._intent_label(category, workloads, clause),
                    "intent_text": clause,
                    "category": category,
                    "workloads": workloads,
                    "extracted_schema": clause_schema,
                    "payload": self._build_intent_payload(payload, extracted_schema, clause_schema, clause),
                }
            )
        return self._collapse_related_intents(intents)

    def _collapse_related_intents(self, intents):
        collapsed = []
        for intent in list(intents or []):
            category = intent.get("category")
            workloads = tuple(sorted(intent.get("workloads") or []))
            merged = False
            for existing in collapsed:
                existing_category = existing.get("category")
                existing_workloads = tuple(sorted(existing.get("workloads") or []))
                if category and existing_category and category == existing_category:
                    merged = True
                elif (
                    workloads
                    and existing_workloads
                    and workloads == existing_workloads
                    and not (category and existing_category and category != existing_category)
                ):
                    merged = True
                elif not category and existing_workloads and workloads and set(workloads).issubset(set(existing_workloads)):
                    merged = True
                elif not existing_category and existing_workloads and workloads and set(existing_workloads).issubset(set(workloads)):
                    merged = True

                if not merged:
                    continue

                combined_text = " ".join(
                    part for part in [existing.get("intent_text"), intent.get("intent_text")] if str(part or "").strip()
                ).strip()
                existing["intent_text"] = combined_text
                existing["label"] = self._intent_label(
                    existing.get("category") or category,
                    existing.get("workloads") or intent.get("workloads"),
                    combined_text or existing.get("label"),
                )
                break
            if not merged:
                collapsed.append(intent)
        return collapsed

    def _detect_mixed_workload_fallback(self, payload, extracted_schema, chat_text):
        extracted_schema = dict(extracted_schema or {})
        workloads = normalize_workloads(extracted_schema.get("workload_types"))
        workload_set = set(workloads)
        if not workload_set.intersection(self.END_USER_WORKLOADS):
            return None
        if not workload_set.intersection(self.NETWORK_WORKLOADS):
            return None

        application_signals = {
            str(signal or "").strip().lower()
            for signal in (extracted_schema.get("application_signals") or [])
            if str(signal or "").strip()
        }
        capability_tags = {
            str(tag or "").strip().lower()
            for tag in (extracted_schema.get("capability_tags") or [])
            if str(tag or "").strip()
        }
        lowered = str(chat_text or "").strip().lower()

        has_end_user_signal = bool(application_signals.intersection(self.END_USER_APPLICATION_SIGNALS)) or any(
            token in lowered for token in self.END_USER_HINT_TOKENS
        )
        has_network_signal = (
            bool(application_signals.intersection(self.NETWORK_APPLICATION_SIGNALS))
            or "branch_connectivity" in capability_tags
            or any(token in lowered for token in self.NETWORK_HINT_TOKENS)
        )
        if not (has_end_user_signal and has_network_signal):
            return None

        shared_budget_reused = payload.get("budget") is not None or extracted_schema.get("budget") is not None
        team_size = extracted_schema.get("team_size")
        quantity = extracted_schema.get("quantity") or team_size
        raw_signals = list(extracted_schema.get("application_signals") or [])
        raw_tags = list(extracted_schema.get("capability_tags") or [])

        end_user_schema = self._build_synthetic_schema(
            extracted_schema=extracted_schema,
            raw_chat="systems for developers",
            preferred_category=None,
            workloads=[workload for workload in workloads if workload in self.END_USER_WORKLOADS],
            application_signals=[
                signal
                for signal in raw_signals
                if str(signal or "").strip().lower() in self.END_USER_APPLICATION_SIGNALS
            ],
            capability_tags=[
                tag
                for tag in raw_tags
                if str(tag or "").strip().lower() in {"local_compute", "high_ram", "always_on"}
            ],
            quantity=quantity,
            purchase_scope="team_rollout",
        )
        network_schema = self._build_synthetic_schema(
            extracted_schema=extracted_schema,
            raw_chat="secure branch access",
            preferred_category="networking",
            workloads=[workload for workload in workloads if workload in self.NETWORK_WORKLOADS],
            application_signals=[
                signal
                for signal in raw_signals
                if str(signal or "").strip().lower() in self.NETWORK_APPLICATION_SIGNALS
            ],
            capability_tags=[
                tag
                for tag in raw_tags
                if str(tag or "").strip().lower() in {"branch_connectivity", "always_on"}
            ],
            quantity=None,
            purchase_scope="site_deployment",
        )

        intents = []
        for index, clause_schema in enumerate((end_user_schema, network_schema), start=1):
            category = normalize_category(clause_schema.get("preferred_category"))
            intent_workloads = normalize_workloads(clause_schema.get("workload_types"))
            clause = str(clause_schema.get("raw_chat") or "").strip()
            intents.append(
                {
                    "group_id": f"intent-{index}",
                    "label": self._intent_label(category, intent_workloads, clause),
                    "intent_text": clause,
                    "category": category,
                    "workloads": intent_workloads,
                    "extracted_schema": clause_schema,
                    "payload": self._build_intent_payload(payload, extracted_schema, clause_schema, clause),
                }
            )

        return {
            "is_multi_intent": True,
            "split_source": "mixed_workload_fallback",
            "shared_budget_reused": shared_budget_reused,
            "intents": intents,
        }

    def _build_synthetic_schema(
        self,
        extracted_schema,
        raw_chat,
        preferred_category,
        workloads,
        application_signals,
        capability_tags,
        quantity,
        purchase_scope,
    ):
        schema = {
            "raw_chat": raw_chat,
            "preferred_category": normalize_category(preferred_category),
            "workload_types": normalize_workloads(workloads),
            "application_signals": list(application_signals or []),
            "capability_tags": list(capability_tags or []),
            "team_size": extracted_schema.get("team_size"),
            "quantity": quantity,
            "purchase_scope": purchase_scope,
            "missing_fields": [],
            "intake_confidence": 1.0,
        }
        return schema

    def _split_clauses(self, chat_text):
        text = str(chat_text or "").strip()
        if not text:
            return []

        raw_parts = []
        last_index = 0
        for match in self.CONNECTOR_PATTERN.finditer(text):
            left = text[last_index:match.start()].strip(" ,.")
            right_preview = text[match.end(): match.end() + 120].strip()
            right_clause = re.split(r"[.;\n]+", right_preview, maxsplit=1)[0].strip()
            if left and (self._has_intent_hint(left) or self._has_intent_hint(right_clause)):
                raw_parts.append(left)
                last_index = match.end()

        raw_parts.append(text[last_index:].strip(" ,."))
        expanded = []
        for clause in raw_parts:
            if not clause:
                continue
            punct_parts = [part.strip(" ,.") for part in self.PUNCTUATION_PATTERN.split(clause) if part.strip(" ,.")]
            candidate_parts = punct_parts if punct_parts else [clause]
            for part in candidate_parts:
                if not part:
                    continue
                segmented = self._split_by_category_tracks(part)
                if segmented:
                    expanded.extend(segmented)
                else:
                    expanded.append(part)
        return [clause for clause in expanded if clause]

    def _split_by_category_tracks(self, text):
        segments = []
        for part in [segment.strip(" ,.") for segment in self.CONNECTOR_PATTERN.split(str(text or "")) if segment.strip(" ,.")]:
            category_hits = self._category_hits(part)
            if len(category_hits) <= 1:
                if self._has_intent_hint(part):
                    segments.append(part)
                continue
            slices = self._slice_part_by_category_hits(part, category_hits)
            if slices:
                segments.extend(slices)
            elif self._has_intent_hint(part):
                segments.append(part)
        deduped = []
        seen = set()
        for segment in segments:
            normalized = " ".join(str(segment or "").split()).strip()
            if not normalized or normalized.lower() in seen:
                continue
            seen.add(normalized.lower())
            deduped.append(normalized)
        return deduped

    def _slice_part_by_category_hits(self, part, category_hits):
        ordered_hits = sorted(category_hits, key=lambda item: item["start"])
        slices = []
        lead_text = part[: ordered_hits[0]["start"]].strip(" ,.")
        for index, hit in enumerate(ordered_hits):
            start = hit["start"]
            end = ordered_hits[index + 1]["start"] if index + 1 < len(ordered_hits) else len(part)
            chunk = part[start:end].strip(" ,.")
            if lead_text and index == 0 and not chunk.lower().startswith(lead_text.lower()):
                chunk = f"{lead_text} {chunk}".strip()
            if self._has_intent_hint(chunk):
                slices.append(chunk)
        return slices

    def _category_hits(self, text):
        lowered = str(text or "").strip().lower()
        hits = []
        for category, tokens in self.CATEGORY_HINTS.items():
            best_start = None
            best_token = None
            for token in tokens:
                pattern = r"(?<![a-z0-9])" + re.escape(token).replace(r"\ ", r"\s+") + r"(?![a-z0-9])"
                match = re.search(pattern, lowered)
                if match and (best_start is None or match.start() < best_start):
                    best_start = match.start()
                    best_token = token
            if best_start is not None:
                hits.append({"category": category, "start": best_start, "token": best_token})
        return hits

    def _has_multiple_category_tracks(self, text):
        categories = {item["category"] for item in self._category_hits(text)}
        return len(categories) >= 2

    def _is_category_choice_uncertainty(self, text, extracted_schema):
        lowered = str(text or "").strip().lower()
        if not lowered or not self._has_multiple_category_tracks(lowered):
            return False
        preferred_category = normalize_category(dict(extracted_schema or {}).get("preferred_category"))
        if preferred_category and preferred_category != "not_sure" and "not sure" not in lowered and "not decided" not in lowered:
            return False
        uncertainty_tokens = (
            "not sure",
            "unsure",
            "not decided",
            "haven't decided",
            "have not decided",
            "can't decide",
            "cannot decide",
            "decide between",
            "choose between",
            "laptops or desktops",
            "desktop or laptop",
            "laptop or desktop",
        )
        return any(token in lowered for token in uncertainty_tokens)

    def _dominant_category_hint(self, text):
        hits = self._category_hits(text)
        if not hits:
            return None
        ordered_hits = sorted(hits, key=lambda item: item["start"])
        return ordered_hits[0]["category"]

    def _should_force_category_split(self, chat_text, extracted_schema):
        extracted_schema = dict(extracted_schema or {})
        if normalize_category(extracted_schema.get("preferred_category")) != "not_sure":
            return False
        if not self._has_multiple_category_tracks(chat_text):
            return False
        workload_count = len(normalize_workloads(extracted_schema.get("workload_types")))
        return workload_count >= 2 or self._has_multiple_category_tracks(chat_text)

    def _has_intent_hint(self, text):
        lowered = str(text or "").strip().lower()
        if not lowered:
            return False
        window = lowered[:90]
        return any(token in window for token in self.INTENT_HINT_TOKENS)

    def _has_product_signal(self, text):
        lowered = str(text or "").strip().lower()
        if not lowered:
            return False
        window = lowered[:90]
        return any(token in window for token in self.PRODUCT_INTENT_TOKENS)

    def _extract_clause_schema(self, clause):
        schema = self.extraction_service.extract(clause, context={})
        schema = dict(schema or {})
        schema["raw_chat"] = clause
        schema["preferred_category"] = normalize_category(schema.get("preferred_category"))
        if not schema.get("preferred_category"):
            hinted_category = self._dominant_category_hint(clause)
            if hinted_category:
                schema["preferred_category"] = hinted_category
        schema["workload_types"] = normalize_workloads(schema.get("workload_types"))
        if not schema.get("workload_types") and schema.get("preferred_category") == "printers":
            schema["workload_types"] = ["document_output"]
        elif not schema.get("workload_types") and schema.get("preferred_category") == "networking":
            schema["workload_types"] = ["network_connectivity"]
        schema["missing_fields"] = []
        schema["intake_confidence"] = 1.0 if schema.get("preferred_category") or schema.get("workload_types") else 0.0
        return schema

    def _build_intent_payload(self, payload, extracted_schema, clause_schema, clause):
        shared_payload = {}
        for key in self.SHARED_KEYS:
            if key in payload and payload.get(key) is not None:
                shared_payload[key] = payload.get(key)
            elif key in extracted_schema and extracted_schema.get(key) is not None:
                shared_payload[key] = extracted_schema.get(key)
        shared_payload["chat_text"] = clause
        shared_payload["raw_chat"] = clause
        shared_payload["extracted_schema"] = clause_schema
        return self.extraction_service.build_procurement_payload(clause_schema, shared_payload)

    def _intent_label(self, category, workloads, clause):
        if category and workloads:
            return f"{category.title()} - {workloads[0].replace('_', ' ').title()}"
        if category:
            return category.title()
        if workloads:
            return workloads[0].replace("_", " ").title()
        return clause[:48]

    def _has_distinct_signals(self, intents):
        categories = {intent.get("category") for intent in intents if intent.get("category")}
        workload_sets = {
            tuple(sorted(intent.get("workloads") or []))
            for intent in intents
            if intent.get("workloads")
        }
        labels = {
            str(intent.get("label") or "").strip().lower()
            for intent in intents
            if str(intent.get("label") or "").strip()
        }
        return len(categories) > 1 or len(workload_sets) > 1 or len(labels) > 1

    def _signal_count(self, clause_schema, category, workloads):
        clause_schema = dict(clause_schema or {})
        return sum(
            1
            for signal in (
                bool(category),
                bool(workloads),
                bool(clause_schema.get("application_signals")),
                bool(clause_schema.get("quantity") or clause_schema.get("team_size")),
                clause_schema.get("budget") is not None,
                bool(clause_schema.get("requested_ram") or clause_schema.get("requested_storage")),
            )
            if signal
        )
