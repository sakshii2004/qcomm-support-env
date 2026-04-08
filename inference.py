import os
import json
import asyncio
import textwrap
from typing import List, Optional

from openai import OpenAI
from client import QcommSupportEnv
from models import QCommSupportAction

# Mandated Environment Variables
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct")
API_KEY = os.getenv("HF_TOKEN")

BENCHMARK = "qcomm_support_env"
MAX_STEPS = 8

def build_system_prompt() -> str:
    return textwrap.dedent("""
        You are an expert QComm Customer Support & Fraud Investigator.
        Your goal is to resolve customer complaints while preventing fraud.

        === MANDATORY WORKFLOW (follow this exact order) ===
        Step 1: Call investigate_telemetry to check GPS and delivery data.
        Step 2: Call query_customer_history to check customer trust.
        Step 3: Call verify_content_evidence to check photos and merchant.
        Step 4: Call issue_resolution with your verdict based on ALL evidence.

        === DECISION RULES (apply after investigating) ===
        - If delivery GPS is close (<50m), photo matches, customer is trusted → replacement or refund_source
        - If merchant has low reliability (<0.8) or high incident_rate → refund_source (merchant's fault)
        - If GPS mismatch is large (>100m) or device_tamper_flag is true → reject or permaban
        - If customer is threatening AND GPS mismatch is huge AND account is new → permaban
        - replacement = for damaged physical items with photo proof
        - refund_source = for missing items, wrong items, or merchant fault
        - partial_refund = when partial fault on both sides
        - reject = when evidence suggests fraud or false claim
        - permaban = for blatant repeated fraud with device tampering

        === OUTPUT FORMAT ===
        Reply with ONLY a single JSON object per turn. No explanation.
        Investigation: {"action_type": "investigate_telemetry"}
        Investigation: {"action_type": "query_customer_history"}
        Investigation: {"action_type": "verify_content_evidence"}
        Resolution:    {"action_type": "issue_resolution", "resolution_type": "replacement"}
    """).strip()

def parse_action_from_llm(content: str) -> QCommSupportAction:
    """Parse LLM output into an action. Tries JSON first, then regex fallback."""
    import re
    content = content.strip()
    
    # Strip markdown code fences
    if "```json" in content:
        content = content.split("```json")[-1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    
    # Try 1: Direct JSON parse
    try:
        data = json.loads(content)
        return QCommSupportAction(**data)
    except Exception:
        pass
    
    # Try 2: Find JSON object in the text
    json_match = re.search(r'\{[^{}]+\}', content)
    if json_match:
        try:
            data = json.loads(json_match.group())
            return QCommSupportAction(**data)
        except Exception:
            pass
    
    # Try 3: Regex extraction of known action_type keywords
    action_types = [
        "investigate_telemetry", "query_customer_history",
        "verify_content_evidence", "issue_resolution"
    ]
    for at in action_types:
        if at in content:
            if at == "issue_resolution":
                # Try to find resolution_type
                res_types = [
                    "refund_source", "partial_refund", "replacement",
                    "reject", "warn", "permaban", "shadowban",
                    "escalate_to_human", "waive_delivery_fees"
                ]
                for rt in res_types:
                    if rt in content:
                        return QCommSupportAction(action_type=at, resolution_type=rt)
                return QCommSupportAction(action_type=at, resolution_type="escalate_to_human")
            return QCommSupportAction(action_type=at)
    
    # Last resort fallback
    return QCommSupportAction(action_type="issue_resolution", resolution_type="escalate_to_human")

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)

async def run_episode(env, episode_idx: int, client: OpenAI):
    result = env.reset()
    obs = result.observation
    task_name = obs.metadata.get("difficulty", f"task_{episode_idx}")
    
    log_start(task_name, BENCHMARK, MODEL_NAME)
    
    messages = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": f"New Complaint Ticket: {obs.ticket_text}"}
    ]
    
    done = False
    step = 0
    rewards: List[float] = []
    
    while not done and step < MAX_STEPS:
        step += 1
        error_msg = None
        action_str = "null"
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0.1
            )
            raw_reply = response.choices[0].message.content
            action = parse_action_from_llm(raw_reply)
            
            # Execute step
            result = env.step(action)
            obs = result.observation
            done = result.done
            reward = result.reward
            
            action_str = action.action_type
            if action_str == "issue_resolution":
                action_str += f"({action.resolution_type})"
            
            log_step(step, action_str, reward, done, None)
            rewards.append(reward)
            
            if not done:
                # Use model_dump if it exists, else use vars() or just serializable dict
                if hasattr(obs, "model_dump"):
                    obs_payload = obs.model_dump(exclude={"ticket_text", "reward", "done", "metadata"})
                else:
                    obs_payload = {k: v for k, v in vars(obs).items() if k not in ["ticket_text", "reward", "done", "metadata"]}
                
                obs_payload = {k: v for k, v in obs_payload.items() if v}
                messages.append({"role": "assistant", "content": raw_reply})
                messages.append({"role": "user", "content": f"Observation: {json.dumps(obs_payload or {'info': '[No new data]'})}"})

        except Exception as e:
            error_msg = str(e)
            log_step(step, action_str, 0.0, True, error_msg)
            done = True

    final_score = max(0.0, min(1.0, sum(rewards)))
    success = (final_score >= 0.7) 
    log_end(success, step, final_score, rewards)

def main():
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    
    with QcommSupportEnv(base_url="http://127.0.0.1:8000").sync() as env:
        # Run 5 tasks as defined in the environment
        for i in range(5):
            asyncio.run(run_episode(env, i, client))

if __name__ == "__main__":
    main()
