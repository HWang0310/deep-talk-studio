"""Core-owned fake-only subprocess adapter with immutable execution evidence."""
from __future__ import annotations
import json, os, signal, subprocess, time, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from .visual_asset_plugin_contract import validate_generation_request, validate_generation_result, validate_suitability_request, validate_suitability_response

def _iso() -> str: return datetime.now(timezone.utc).isoformat()
def _locator(kind: str, request_id: str, name: str = "") -> str: return f"local-plugin-{kind}://{request_id}" + ("/" + name if name else "")

def resolve_plugin_version(plugin: Mapping[str, Any]) -> str:
    try:
        result=subprocess.run(list(plugin["plugin_version_command"]),cwd=plugin["plugin_root"],env={**os.environ,**dict(plugin.get("environment",{}))},capture_output=True,text=True,timeout=float(plugin["timeout_seconds"]),check=True)
    except (OSError,subprocess.SubprocessError) as exc: raise ValueError("plugin_version_resolution_failed") from exc
    version=result.stdout.strip()
    if not version or "\n" in version: raise ValueError("plugin_version_invalid")
    return version

def run_visual_plugin(plugin: Mapping[str, Any], *, operation: str, opportunity: Mapping[str, Any], job_root: Path, proposal_id: str | None = None, plugin_config_digest: str = "") -> dict:
    if operation not in {"suitability","generation"}: raise ValueError("operation 必须是 suitability 或 generation")
    if operation=="generation" and (not isinstance(proposal_id,str) or not proposal_id): raise ValueError("generation 需要有效 proposal_id")
    request_id="REQ-"+uuid.uuid4().hex; started=_iso(); started_clock=time.monotonic()
    job=Path(job_root)/request_id; output=job/"output"; job.mkdir(parents=True,exist_ok=False); output.mkdir()
    try: version=resolve_plugin_version(plugin)
    except ValueError as exc: return _failure(plugin,request_id,operation,job,started,started_clock,str(exc),plugin_config_digest)
    request={"contract_version":"visual-asset-plugin-contract/1","request_id":request_id,"opportunity":dict(opportunity)}
    if operation=="generation": request["proposal_id"]=proposal_id; validate_generation_request(request)
    else: validate_suitability_request(request)
    request_path=job/"request.json"; result_path=job/"result.json"; request_path.write_text(json.dumps(request,ensure_ascii=False,sort_keys=True),encoding="utf-8")
    command=list(plugin["argv_prefix"])+["--request",str(request_path),"--result",str(result_path),"--output-dir",str(output)]
    try:
        process=subprocess.Popen(command,cwd=plugin["plugin_root"],env={**os.environ,**dict(plugin.get("environment",{}))},text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        stdout,stderr=process.communicate(timeout=float(plugin["timeout_seconds"]))
    except FileNotFoundError: return _failure(plugin,request_id,operation,job,started,started_clock,"missing_executable",plugin_config_digest)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid,signal.SIGTERM)
        try: stdout,stderr=process.communicate(timeout=1)
        except subprocess.TimeoutExpired: os.killpg(process.pid,signal.SIGKILL); stdout,stderr=process.communicate()
        _logs(job,stdout,stderr); return _failure(plugin,request_id,operation,job,started,started_clock,"timeout",plugin_config_digest)
    _logs(job,stdout,stderr)
    if process.returncode: return _failure(plugin,request_id,operation,job,started,started_clock,"non_zero_exit",plugin_config_digest,version)
    if not result_path.is_file(): return _failure(plugin,request_id,operation,job,started,started_clock,"missing_result",plugin_config_digest,version)
    try:
        response=json.loads(result_path.read_text(encoding="utf-8"))
        if operation=="suitability": validate_suitability_response(response)
        else: validate_generation_result(response,opportunity)
        if response["request_id"]!=request_id or response["opportunity_id"]!=opportunity["opportunity_id"] or response["plugin_id"]!=plugin["plugin_id"] or response["plugin_version"]!=version or (operation=="generation" and response["proposal_id"]!=proposal_id): raise ValueError("correlation")
    except Exception: return _failure(plugin,request_id,operation,job,started,started_clock,"invalid_result",plugin_config_digest,version)
    return {"execution":_execution(plugin,version,plugin_config_digest,request_id,operation,job,started,started_clock,"COMPLETED",False,"completed"),"raw_response":response,"request_snapshot":request,"_output_root":str(output)}

def _execution(plugin: Mapping[str,Any],version:str,config_digest:str,request_id:str,operation:str,job:Path,started:str,started_clock:float,status:str,retryable:bool,reason:str)->dict:
    return {"plugin_id":plugin["plugin_id"],"resolved_plugin_version":version,"config_digest":config_digest,"request_id":request_id,"operation":operation,"job_locator":_locator("job",request_id),"request_locator":_locator("request",request_id,"request.json"),"result_locator":_locator("result",request_id,"result.json"),"stdout_locator":_locator("log",request_id,"stdout.log"),"stderr_locator":_locator("log",request_id,"stderr.log"),"output_locator":_locator("output",request_id),"status":status,"retryable":retryable,"reason":reason,"started_at":started,"finished_at":_iso(),"runtime_duration_ms":int(round((time.monotonic()-started_clock)*1000))}

def _logs(job:Path,stdout:str,stderr:str)->None:
    (job/"stdout.log").write_text(stdout[-65536:],encoding="utf-8"); (job/"stderr.log").write_text(stderr[-65536:],encoding="utf-8")
def _failure(plugin:Mapping[str,Any],request_id:str,operation:str,job:Path,started:str,started_clock:float,reason:str,config_digest:str,version:str="")->dict:
    return {"execution":_execution(plugin,version,config_digest,request_id,operation,job,started,started_clock,"FAILED",True,reason),"raw_response":None,"request_snapshot":None,"_output_root":str(job/"output")}
