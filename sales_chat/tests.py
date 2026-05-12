import asyncio
import json
import os
import unittest

from asgiref.testing import ApplicationCommunicator

from ai_configurator.catalog.services.connection import get_catalog_client

import ai_configurator.sales_chat.websocket_consumer as websocket_consumer
from ai_configurator.procurement.services.recommendation_service import ProcurementRecommendationService
from ai_configurator.sales_chat.services.sales_service import SalesService
from ai_configurator.sales_chat.services.ui_guidance import build_narrowing_guidance
from ai_configurator.sales_chat.websocket_consumer import SalesBotConsumer
from test_support.catalog_dataset import build_catalog_repository
from test_support.fake_catalog import build_sample_catalog_repository


def build_recommendation_service(catalog_size="small"):
    if str(catalog_size or "").strip().lower() == "small":
        repository = build_sample_catalog_repository()
    else:
        repository = build_catalog_repository(catalog_size)
    service = ProcurementRecommendationService(catalog_repository=repository)
    service.extraction_service.llm_client.api_key = ""
    service.explanation_service.llm_client.api_key = ""
    service.followup_service.llm_client.api_key = ""
    return service


def build_sales_service(catalog_size="small"):
    service = SalesService()
    service.recommendation_service = build_recommendation_service(catalog_size=catalog_size)
    service.extraction_service = service.recommendation_service.extraction_service
    service.followup_service = service.recommendation_service.followup_service
    service.clarification_service = service.recommendation_service.clarification_service
    service.extraction_service.llm_client.api_key = ""
    service.followup_service.llm_client.api_key = ""
    return service


class SalesServiceEndToEndTests(unittest.TestCase):
    def setUp(self):
        self.service = build_sales_service(catalog_size="small")

    def test_default_sales_service_uses_fake_catalog_when_mongo_is_unconfigured(self):
        original_catalog_uri = os.environ.get("CATALOG_MONGODB_URI")
        original_products_uri = os.environ.get("PRODUCTS_MONGODB_URI")
        original_catalog_size = os.environ.get("PROCUREMENT_FAKE_CATALOG_SIZE")
        try:
            os.environ.pop("CATALOG_MONGODB_URI", None)
            os.environ.pop("PRODUCTS_MONGODB_URI", None)
            os.environ["PROCUREMENT_FAKE_CATALOG_SIZE"] = "small"
            get_catalog_client.cache_clear()

            service = SalesService()
            service.extraction_service.llm_client.api_key = ""
            service.followup_service.llm_client.api_key = ""
            service.recommendation_service.explanation_service.llm_client.api_key = ""

            payload = service.get_response_payload(
                "We need laptops for 15 software developers under 6500 each",
                "session-default-runtime",
            )

            self.assertEqual(payload["response_type"], "question")
            self.assertEqual(payload["recommendations"][0]["name"], "Developer Pro 15")
        finally:
            if original_catalog_uri is None:
                os.environ.pop("CATALOG_MONGODB_URI", None)
            else:
                os.environ["CATALOG_MONGODB_URI"] = original_catalog_uri
            if original_products_uri is None:
                os.environ.pop("PRODUCTS_MONGODB_URI", None)
            else:
                os.environ["PRODUCTS_MONGODB_URI"] = original_products_uri
            if original_catalog_size is None:
                os.environ.pop("PROCUREMENT_FAKE_CATALOG_SIZE", None)
            else:
                os.environ["PROCUREMENT_FAKE_CATALOG_SIZE"] = original_catalog_size
            get_catalog_client.cache_clear()

    def test_sales_service_extracts_meaningful_procurement_brief_without_llm(self):
        session_id = "session-rich"

        welcome = self.service.get_response("", session_id)
        self.assertIn("Tell me what you need to buy", welcome)

        reply = self.service.get_response(
            "We need 12 lightweight laptops for software developers under 6500 each "
            "with 16GB RAM and 512GB SSD with premium support and moderate growth",
            session_id,
        )

        prefs = self.service.session_answers[session_id]
        self.assertEqual(prefs["preferred_category"], "laptops")
        self.assertEqual(prefs["workload_types"], ["software_development"])
        self.assertEqual(prefs["budget"], 6500)
        self.assertEqual(prefs["team_size"], 12)
        self.assertEqual(prefs["quantity"], 12)
        self.assertEqual(prefs["requested_ram"], "16GB")
        self.assertEqual(prefs["requested_storage"], "512GB")
        self.assertEqual(prefs["portability_need"], "high")
        self.assertEqual(prefs["support_expectation"], "premium")
        self.assertEqual(prefs["growth_expectation"], "moderate_growth")
        self.assertIn("Developer Pro 15", reply)
        self.assertIn("SKU-LAP-002-P1", reply)
        self.assertIn("Explanation:", reply)
        self.assertIn("If you move lower:", reply)
        self.assertIn("Overall rationale:", reply)
        self.assertIn("12 seats", reply)

    def test_sales_service_returns_recommendation_and_refinement_prompt_when_only_non_blocking_signals_are_missing(self):
        session_id = "session-followup"

        self.service.get_response("", session_id)
        payload = self.service.get_response_payload(
            "We need laptops for 15 software developers under 6500 each",
            session_id,
        )

        self.assertEqual(payload["response_type"], "question")
        self.assertIn("Which apps or tools matter most", payload["response"])
        self.assertEqual(payload["recommendations"][0]["name"], "Developer Pro 15")
        self.assertIn("application_profile", payload["readiness"]["missing_signals"])

    def test_sales_service_recommendation_payload_exposes_current_procurement_metadata(self):
        session_id = "session-current-metadata"

        self.service.get_response("", session_id)
        payload = self.service.get_response_payload(
            "We need laptops for 15 software developers under 6500 each",
            session_id,
        )

        self.assertEqual(payload["response_type"], "question")
        self.assertEqual(payload["recommendation_mode"], "provisional_recommendation")
        self.assertEqual(payload["requirements"]["channel"], "websocket")
        self.assertEqual(payload["meta"]["selected_template"]["template_id"], "developer-team-starter-v1")
        self.assertEqual(payload["meta"]["selected_template"]["template_match_quality"], "exact")
        self.assertTrue(payload["meta"]["selected_template"]["template_selection_debug"])
        self.assertTrue(payload["template_candidates"])
        self.assertTrue(payload["recommendations"])

    def test_sales_service_payload_includes_streamlit_style_llm_stats(self):
        session_id = "session-llm-stats"

        welcome_payload = self.service.get_response_payload("", session_id)
        self.assertIn("llm_stats", welcome_payload)
        self.assertEqual(
            set(welcome_payload["llm_stats"].keys()),
            {"provider", "model", "available", "extraction", "followup", "explanation"},
        )

        payload = self.service.get_response_payload(
            "We need laptops for 15 software developers under 6500 each",
            session_id,
        )

        self.assertIn("llm_stats", payload)
        self.assertEqual(payload["llm_stats"]["provider"], "groq")
        self.assertFalse(payload["llm_stats"]["available"])
        self.assertIsInstance(payload["llm_stats"]["extraction"], dict)
        self.assertIsInstance(payload["llm_stats"]["followup"], dict)
        self.assertIsInstance(payload["llm_stats"]["explanation"], dict)
        self.assertIn("text_calls", payload["llm_stats"]["extraction"])
        self.assertIn("text_calls", payload["llm_stats"]["followup"])
        self.assertIn("text_calls", payload["llm_stats"]["explanation"])

    def test_sales_service_asks_for_app_tool_mix_as_refinement_for_broad_developer_brief(self):
        session_id = "session-app-profile"

        self.service.get_response("", session_id)
        payload = self.service.get_response_payload(
            "Need laptops for 8 software developers under 7000 each",
            session_id,
        )

        self.assertEqual(payload["response_type"], "question")
        self.assertTrue(payload["readiness"]["is_ready"])
        self.assertIn("application_profile", payload["readiness"]["missing_signals"])
        self.assertEqual(payload["readiness"]["routing_recommendation"], "recommend_with_one_refinement")
        self.assertIn("Which apps or tools matter most", payload["response"])
        self.assertEqual(payload["recommendations"][0]["name"], "Developer Pro 15")

    def test_sales_service_asks_work_profile_before_recommending_category_budget_and_team_size_only(self):
        session_id = "session-use-case"

        self.service.get_response("", session_id)
        payload = self.service.get_response_payload(
            "Need laptops for 20 people under 4500 each",
            session_id,
        )

        self.assertEqual(payload["response_type"], "question")
        self.assertIn("workload_or_application_profile", payload["readiness"]["missing_signals"])
        self.assertIn("What kind of work will these systems support", payload["response"])
        self.assertTrue(payload["ui_guidance"])
        self.assertEqual(payload["ui_guidance"][0]["title"], "Narrow Down The Work Profile")

    def test_sales_service_preserves_team_size_when_budget_reply_contains_lakhs(self):
        session_id = "session-lakhs"

        self.service.get_response("", session_id)
        first = self.service.get_response_payload("i need to buy laptops for my team", session_id)
        second = self.service.get_response_payload("i am basically a startup for software development", session_id)
        third = self.service.get_response_payload("there will be almost 20 people in my company", session_id)
        final = self.service.get_response_payload("i have a overall budget of 2 lakhs", session_id)

        self.assertEqual(first["response_type"], "question")
        self.assertEqual(second["response_type"], "question")
        self.assertEqual(third["response_type"], "question")
        self.assertEqual(final["response_type"], "question")
        self.assertEqual(final["requirements"]["team_size"], 20)
        self.assertEqual(final["requirements"]["quantity"], 20)
        self.assertEqual(final["requirements"]["budget"], 200000)
        self.assertIsNone(final["requirements"]["growth_expectation"])
        self.assertIn("20 seats", final["summary"])
        self.assertNotIn("2 seats", final["summary"])
        self.assertTrue(final["recommendations"])
        self.assertEqual(final["recommendations"][0]["name"], "Developer Pro 15")

    def test_sales_service_accepts_terse_lakh_budget_reply_for_total_budget_question(self):
        session_id = "session-terse-total-budget"

        self.service.get_response("", session_id)
        first = self.service.get_response_payload(
            "Need laptops for 40 office users",
            session_id,
        )

        self.assertEqual(first["response_type"], "question")
        self.assertIn("budget", first["response"].lower())

        self.service.followup_service.next_question = lambda prefs, readiness: (
            "What is your total budget for purchasing the 40 laptops?"
        )
        final = self.service.get_response_payload("2 lakh", session_id)

        self.assertEqual(final["response_type"], "recommendation")
        self.assertEqual(final["requirements"]["budget"], 200000)
        self.assertEqual(final["requirements"]["budget_scope"], "project_total")
        self.assertEqual(final["requirements"]["team_size"], 40)
        self.assertEqual(final["requirements"]["quantity"], 40)
        self.assertIn("40 seats", final["summary"])
        self.assertTrue(final["recommendations"])

    def test_sales_service_accepts_yes_for_budget_confirmation_question(self):
        session_id = "session-budget-confirmation"

        self.service.get_response("", session_id)
        first = self.service.get_response_payload(
            "Need 20 laptops for office users",
            session_id,
        )

        self.assertEqual(first["response_type"], "question")

        self.service.followup_service.next_question = lambda prefs, readiness: (
            "Can you confirm the total budget for the 20 laptops is 3 lakh INR?"
        )
        final = self.service.get_response_payload("yes", session_id)

        self.assertEqual(final["response_type"], "recommendation")
        self.assertEqual(final["requirements"]["budget"], 300000)
        self.assertEqual(final["requirements"]["budget_scope"], "project_total")
        self.assertEqual(final["requirements"]["team_size"], 20)
        self.assertEqual(final["requirements"]["quantity"], 20)
        self.assertIn("20 seats", final["summary"])
        self.assertTrue(final["recommendations"])

    def test_sales_service_can_use_safe_llm_fallback_for_ambiguous_budget_confirmation_reply(self):
        session_id = "session-llm-budget-confirmation"

        class FakeReplyLlm:
            def __init__(self):
                self.calls = []

            def is_available(self):
                return True

            def invoke_text(self, prompt_name, variables):
                return None

            def invoke_json(self, prompt_name, variables):
                self.calls.append((prompt_name, dict(variables or {})))
                return {"rewrite": "My overall budget is 3 lakh INR."}

        fake_llm = FakeReplyLlm()
        self.service.followup_service.llm_client = fake_llm

        self.service.get_response("", session_id)
        first = self.service.get_response_payload(
            "Need 20 laptops for office users",
            session_id,
        )

        self.assertEqual(first["response_type"], "question")
        self.assertIn("budget", first["response"].lower())

        self.service.followup_service.next_question = lambda prefs, readiness: (
            "Can you confirm the total budget for the 20 laptops is 3 lakh INR?"
        )
        final = self.service.get_response_payload("works for us", session_id)

        self.assertEqual(final["response_type"], "recommendation")
        self.assertEqual(final["requirements"]["budget"], 300000)
        self.assertEqual(final["requirements"]["budget_scope"], "project_total")
        self.assertTrue(fake_llm.calls)
        self.assertTrue(final["recommendations"])

    def test_sales_service_preserves_growth_in_budget_followup_reply(self):
        session_id = "session-office-chatty"

        self.service.get_response("", session_id)
        first = self.service.get_response_payload(
            "hey, around 20 people, just normal office work, need affordable laptops",
            session_id,
        )

        self.assertEqual(first["response_type"], "question")

        final = self.service.get_response_payload(
            "budget is 4500 each and steady growth",
            session_id,
        )

        self.assertEqual(final["response_type"], "recommendation")
        self.assertEqual(final["requirements"]["budget_scope"], "per_unit")
        self.assertEqual(final["requirements"]["growth_expectation"], "steady")
        self.assertEqual(final["requirements"]["purchase_scope"], "team_rollout")
        self.assertEqual(final["recommendations"][0]["name"], "OfficeBook 14")

    def test_sales_service_replaces_ambiguous_scope_after_category_clarification(self):
        session_id = "session-ambiguous-office"

        self.service.get_response("", session_id)
        first = self.service.get_response_payload(
            "We've got about 20 new people joining soon. It's mostly email, docs, meetings, browser apps, "
            "the usual. I haven't decided between laptops and desktops yet, and I want to keep it sensible.",
            session_id,
        )
        second = self.service.get_response_payload("Let's go with laptops.", session_id)
        final = self.service.get_response_payload("Budget is around 4500 each and steady growth.", session_id)

        self.assertEqual(first["response_type"], "question")
        self.assertEqual(second["response_type"], "question")
        self.assertEqual(final["response_type"], "recommendation")
        self.assertEqual(final["requirements"]["preferred_categories"], ["laptops"])
        self.assertEqual(final["requirements"]["purchase_scope"], "team_rollout")
        self.assertEqual(final["requirements"]["budget_scope"], "per_unit")
        self.assertEqual(final["recommendations"][0]["name"], "OfficeBook 14")
        self.assertNotIn("Bundle candidate was rejected", final["summary"])

    def test_sales_service_keeps_limited_availability_option_for_urgent_rollout(self):
        session_id = "session-urgent-rollout"

        self.service.get_response("", session_id)
        first = self.service.get_response_payload(
            "Need laptops for 18 software developers under 7000 each and we need them available now.",
            session_id,
        )
        final = self.service.get_response_payload(
            "Moderate growth over the next year.",
            session_id,
        )

        self.assertEqual(first["response_type"], "question")
        self.assertEqual(final["response_type"], "question")
        self.assertEqual(final["recommendations"][0]["name"], "Developer Pro 15")
        self.assertEqual(final["recommendations"][0]["fit_status"], "limited_availability")

    def test_sales_service_returns_expert_review_for_websocket_coverage_gap(self):
        session_id = "session-coverage-gap"

        self.service.get_response("", session_id)
        payload = self.service.get_response_payload(
            "Need one server for virtualization in stock now under 20000",
            session_id,
        )

        self.assertEqual(payload["response_type"], "recommendation")
        self.assertEqual(payload["recommendation_mode"], "expert_review_recommended")
        self.assertTrue(payload["expert_review_eligible"])
        self.assertEqual(
            payload["meta"]["selected_template"]["template_id"],
            "server-virtualization-starter-v1",
        )
        self.assertEqual(payload["meta"]["selected_template"]["template_match_quality"], "coverage_gap")
        self.assertEqual(payload["meta"]["selected_template"]["gap_type"], "unsupported_urgency")
        self.assertTrue(payload["meta"]["selected_template"]["template_selection_debug"])

    def test_sales_service_returns_ui_guidance_with_recommendation_refinement(self):
        session_id = "session-guidance-refinement"

        self.service.get_response("", session_id)
        payload = self.service.get_response_payload(
            "We need laptops for 15 software developers under 6500 each",
            session_id,
        )

        self.assertEqual(payload["response_type"], "question")
        self.assertTrue(payload["ui_guidance"])
        titles = [section["title"] for section in payload["ui_guidance"]]
        self.assertIn("Narrow Down The App Mix", titles)
        self.assertIn("Tune The Recommendation", titles)

    def test_sales_service_supports_printer_recommendations_on_corrected_json_catalog(self):
        session_id = "session-printer-corrected-json"
        service = build_sales_service(catalog_size="corrected_json")

        service.get_response("", session_id)
        payload = service.get_response_payload(
            "Need a shared office printer for 25 users under 30000",
            session_id,
        )

        self.assertEqual(payload["response_type"], "recommendation")
        self.assertEqual(payload["requirements"]["currency"], "INR")
        self.assertEqual(payload["recommendations"][0]["category"], "printers")
        self.assertIn("printer", payload["response"].lower())
        self.assertEqual(
            payload["meta"]["selected_template"]["template_id"],
            "office-printing-starter-v1",
        )

    def test_sales_service_supports_headsets_but_not_webcams_on_corrected_json_catalog(self):
        session_id = "session-accessories-corrected-json"
        service = build_sales_service(catalog_size="corrected_json")

        service.get_response("", session_id)
        headset_payload = service.get_response_payload(
            "Need 15 wireless headsets for a support team under 5000 each",
            session_id,
        )

        self.assertEqual(headset_payload["response_type"], "recommendation")
        self.assertEqual(headset_payload["recommendations"][0]["category"], "accessories")
        self.assertIn("headset", headset_payload["response"].lower())

        rejected_payload = service.get_response_payload(
            "Need 10 webcams for a support team under 5000 each",
            "session-webcam-rejection",
        )

        self.assertEqual(rejected_payload["response_type"], "question")
        self.assertFalse(rejected_payload["recommendations"])
        self.assertIn("growth", rejected_payload["response"].lower())

    def test_sales_service_multi_intent_bundle_returns_grouped_marketplace_wide_result(self):
        session_id = "session-multi-intent-headset-bundle"
        service = build_sales_service(catalog_size="corrected_json")

        service.get_response("", session_id)
        payload = service.get_response_payload(
            (
                "Need 10 laptops for software developers using VS Code and Docker under 90000 each "
                "and 10 wireless headsets under 5000 each with moderate growth and balanced performance"
            ),
            session_id,
        )

        self.assertEqual(payload["response_type"], "recommendation")
        self.assertGreaterEqual(len(payload.get("recommendation_groups") or []), 2)
        self.assertTrue(payload.get("meta", {}).get("multi_intent", {}).get("bundle_validated"))
        self.assertFalse(payload.get("meta", {}).get("catalog_observability", {}).get("store_scope_applied"))
        group_labels = [group.get("label", "") for group in payload.get("recommendation_groups") or []]
        self.assertTrue(any("Laptop" in label or "Laptops" in label for label in group_labels))
        self.assertTrue(
            any(
                "Accessory" in label or "Accessories" in label or "Headset" in label
                for label in group_labels
            )
        )


class SalesUiGuidanceTests(unittest.TestCase):
    def test_guidance_offers_work_profile_shortcuts_when_work_profile_is_missing(self):
        sections = build_narrowing_guidance(
            {"preferred_category": "laptops"},
            {"missing_signals": ["workload_or_application_profile"], "is_ready": False},
        )

        self.assertTrue(sections)
        self.assertEqual(sections[0]["title"], "Narrow Down The Work Profile")
        labels = [option["label"] for option in sections[0]["options"]]
        self.assertIn("Software development", labels)
        self.assertIn("Office apps", labels)

    def test_guidance_offers_application_profile_shortcuts_for_developer_workload(self):
        sections = build_narrowing_guidance(
            {"preferred_category": "laptops", "workload_types": ["software_development"]},
            {"missing_signals": ["application_profile"], "is_ready": True},
        )

        self.assertTrue(sections)
        self.assertEqual(sections[0]["title"], "Narrow Down The App Mix")
        labels = [option["label"] for option in sections[0]["options"]]
        self.assertIn("Backend dev", labels)
        self.assertIn("Full-stack web", labels)


class SalesBotConsumerAsgiTests(unittest.TestCase):
    def setUp(self):
        self.original_sales_service = websocket_consumer.sales_service
        websocket_consumer.sales_service = build_sales_service(catalog_size="small")

    def tearDown(self):
        websocket_consumer.sales_service = self.original_sales_service

    def test_websocket_flow_reaches_recommendation_and_structured_refinement_prompt(self):
        async def scenario():
            scope = {
                "type": "websocket",
                "path": "/ws/sales-bot/",
                "query_string": b"",
                "headers": [],
                "subprotocols": [],
            }
            communicator = ApplicationCommunicator(SalesBotConsumer.as_asgi(), scope)

            await communicator.send_input({"type": "websocket.connect"})
            accepted = await communicator.receive_output(timeout=1)
            self.assertEqual(accepted["type"], "websocket.accept")

            welcome_event = await communicator.receive_output(timeout=1)
            welcome_payload = json.loads(welcome_event["text"])
            self.assertIn("Tell me what you need to buy", welcome_payload["response"])
            self.assertEqual(welcome_payload["response_type"], "question")
            self.assertIn("llm_stats", welcome_payload)
            self.assertEqual(
                set(welcome_payload["llm_stats"].keys()),
                {"provider", "model", "available", "extraction", "followup", "explanation"},
            )

            await communicator.send_input(
                {
                    "type": "websocket.receive",
                    "text": json.dumps(
                        {
                            "userSelection": "We need laptops for 15 software developers under 6500 each"
                        }
                    ),
                }
            )
            recommendation_event = await communicator.receive_output(timeout=1)
            recommendation_payload = json.loads(recommendation_event["text"])
            self.assertEqual(recommendation_payload["response_type"], "question")
            self.assertIn("Which apps or tools matter most", recommendation_payload["response"])
            self.assertEqual(recommendation_payload["recommendations"][0]["name"], "Developer Pro 15")
            self.assertIn("explanation", recommendation_payload["recommendations"][0])
            self.assertIn("downgrade_implications", recommendation_payload["recommendations"][0])
            self.assertIn("summary", recommendation_payload)
            self.assertIn("assumptions", recommendation_payload)
            self.assertIn("readiness", recommendation_payload)
            self.assertTrue(recommendation_payload["readiness"]["is_ready"])
            self.assertIn("growth_expectation", recommendation_payload["readiness"]["missing_signals"])
            self.assertIn("llm_stats", recommendation_payload)
            self.assertFalse(recommendation_payload["llm_stats"]["available"])
            self.assertIn("text_calls", recommendation_payload["llm_stats"]["extraction"])
            self.assertIn("text_calls", recommendation_payload["llm_stats"]["followup"])
            self.assertIn("text_calls", recommendation_payload["llm_stats"]["explanation"])
            self.assertIn("ui_guidance", recommendation_payload)
            guidance_titles = [section["title"] for section in recommendation_payload["ui_guidance"]]
            self.assertIn("Narrow Down The App Mix", guidance_titles)
            self.assertIn("Tune The Recommendation", guidance_titles)

            await communicator.send_input({"type": "websocket.disconnect", "code": 1000})
            await communicator.wait(timeout=1)

        asyncio.run(scenario())

    def test_websocket_payload_exposes_current_template_metadata(self):
        async def scenario():
            scope = {
                "type": "websocket",
                "path": "/ws/sales-bot/",
                "query_string": b"",
                "headers": [],
                "subprotocols": [],
            }
            communicator = ApplicationCommunicator(SalesBotConsumer.as_asgi(), scope)

            await communicator.send_input({"type": "websocket.connect"})
            await communicator.receive_output(timeout=1)
            await communicator.receive_output(timeout=1)

            await communicator.send_input(
                {
                    "type": "websocket.receive",
                    "text": json.dumps(
                        {"userSelection": "We need laptops for 15 software developers under 6500 each"}
                    ),
                }
            )
            recommendation_event = await communicator.receive_output(timeout=1)
            recommendation_payload = json.loads(recommendation_event["text"])

            self.assertEqual(recommendation_payload["recommendation_mode"], "provisional_recommendation")
            self.assertEqual(
                recommendation_payload["meta"]["selected_template"]["template_id"],
                "developer-team-starter-v1",
            )
            self.assertEqual(
                recommendation_payload["meta"]["selected_template"]["template_match_quality"],
                "exact",
            )
            self.assertTrue(
                recommendation_payload["meta"]["selected_template"]["template_selection_debug"]
            )
            self.assertEqual(recommendation_payload["requirements"]["channel"], "websocket")

            await communicator.send_input({"type": "websocket.disconnect", "code": 1000})
            await communicator.wait(timeout=1)

        asyncio.run(scenario())

    def test_websocket_flow_surfaces_expert_review_for_coverage_gap(self):
        async def scenario():
            scope = {
                "type": "websocket",
                "path": "/ws/sales-bot/",
                "query_string": b"",
                "headers": [],
                "subprotocols": [],
            }
            communicator = ApplicationCommunicator(SalesBotConsumer.as_asgi(), scope)

            await communicator.send_input({"type": "websocket.connect"})
            await communicator.receive_output(timeout=1)
            await communicator.receive_output(timeout=1)

            await communicator.send_input(
                {
                    "type": "websocket.receive",
                    "text": json.dumps(
                        {"userSelection": "Need one server for virtualization in stock now under 20000"}
                    ),
                }
            )
            recommendation_event = await communicator.receive_output(timeout=1)
            recommendation_payload = json.loads(recommendation_event["text"])

            self.assertEqual(recommendation_payload["response_type"], "recommendation")
            self.assertEqual(recommendation_payload["recommendation_mode"], "expert_review_recommended")
            self.assertTrue(recommendation_payload["expert_review_eligible"])
            self.assertEqual(
                recommendation_payload["meta"]["selected_template"]["template_id"],
                "server-virtualization-starter-v1",
            )
            self.assertEqual(
                recommendation_payload["meta"]["selected_template"]["template_match_quality"],
                "coverage_gap",
            )
            self.assertEqual(
                recommendation_payload["meta"]["selected_template"]["gap_type"],
                "unsupported_urgency",
            )

            await communicator.send_input({"type": "websocket.disconnect", "code": 1000})
            await communicator.wait(timeout=1)

        asyncio.run(scenario())

    def test_websocket_flow_supports_corrected_json_printer_recommendation(self):
        async def scenario():
            scope = {
                "type": "websocket",
                "path": "/ws/sales-bot/",
                "query_string": b"",
                "headers": [],
                "subprotocols": [],
            }
            websocket_consumer.sales_service = build_sales_service(catalog_size="corrected_json")
            communicator = ApplicationCommunicator(SalesBotConsumer.as_asgi(), scope)

            await communicator.send_input({"type": "websocket.connect"})
            await communicator.receive_output(timeout=1)
            await communicator.receive_output(timeout=1)

            await communicator.send_input(
                {
                    "type": "websocket.receive",
                    "text": json.dumps(
                        {"userSelection": "Need a shared office printer for 25 users under 30000"}
                    ),
                }
            )
            recommendation_event = await communicator.receive_output(timeout=1)
            recommendation_payload = json.loads(recommendation_event["text"])

            self.assertEqual(recommendation_payload["response_type"], "recommendation")
            self.assertEqual(recommendation_payload["requirements"]["channel"], "websocket")
            self.assertEqual(recommendation_payload["recommendations"][0]["category"], "printers")
            self.assertEqual(
                recommendation_payload["meta"]["selected_template"]["template_id"],
                "office-printing-starter-v1",
            )

            await communicator.send_input({"type": "websocket.disconnect", "code": 1000})
            await communicator.wait(timeout=1)

        asyncio.run(scenario())

    def test_websocket_flow_rejects_out_of_scope_webcam_request(self):
        async def scenario():
            scope = {
                "type": "websocket",
                "path": "/ws/sales-bot/",
                "query_string": b"",
                "headers": [],
                "subprotocols": [],
            }
            websocket_consumer.sales_service = build_sales_service(catalog_size="corrected_json")
            communicator = ApplicationCommunicator(SalesBotConsumer.as_asgi(), scope)

            await communicator.send_input({"type": "websocket.connect"})
            await communicator.receive_output(timeout=1)
            await communicator.receive_output(timeout=1)

            await communicator.send_input(
                {
                    "type": "websocket.receive",
                    "text": json.dumps(
                        {"userSelection": "Need 10 webcams for a support team under 5000 each"}
                    ),
                }
            )
            recommendation_event = await communicator.receive_output(timeout=1)
            recommendation_payload = json.loads(recommendation_event["text"])

            self.assertEqual(recommendation_payload["response_type"], "question")
            self.assertFalse(recommendation_payload.get("recommendations"))
            self.assertIn("growth", recommendation_payload["response"].lower())

            await communicator.send_input({"type": "websocket.disconnect", "code": 1000})
            await communicator.wait(timeout=1)

        asyncio.run(scenario())
