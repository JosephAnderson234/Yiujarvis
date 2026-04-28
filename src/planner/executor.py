from src.error_logger import log_exception


class PlanExecutor:
    def __init__(self, registry):
        self.registry = registry

    def run(self, plan):
        results = []
        plan.context.setdefault("step_results", [])

        for step in plan.steps:
            try:
                if not step.should_run(plan.context):
                    skipped = f"[skipped] {step.action}"
                    results.append(skipped)
                    plan.context["step_results"].append({"step": step.to_dict(), "result": skipped})
                    continue

                result = self.registry.execute(step.action, **step.params)
                plan.context["last_result"] = result
                plan.context["step_results"].append({"step": step.to_dict(), "result": result})
                results.append(result)
            except Exception:
                log_exception(f"Error ejecutando el paso {step.action}")
                failure = f"No se pudo ejecutar {step.action}"
                plan.context["step_results"].append({"step": step.to_dict(), "result": failure})
                results.append(failure)

        return results