"""Verbs plugin: the deterministic-job registry over HTTP.

No tab of its own. Verbs are not a place you go, they are things you run from
wherever you already are — the command palette, a ticket card, eventually a lane
button. Registering a tab for them would add a destination nobody wants to
visit.

Running one is a POST because it can mutate, and because a GET that changes
state is a GET a browser will happily repeat.
"""

from .. import audit
from .. import jobs as jobs_mod
from .. import verbs as verbs_mod
from ..plugins.base import Plugin


def apply(ctx):
    repo_root = ctx.repo_root

    def listing(req):
        """Every verb, each marked runnable-or-not for the given ticket.

        `available` plus `reason` is what lets the palette grey a row and say
        why, instead of offering something that fails on click.
        """
        return {"verbs": verbs_mod.list_verbs(repo_root,
                                              ticket=req.query.get("ticket"))}

    def run(req, verb_id):
        body = dict(req.body or {})
        ticket = body.pop("ticket", None) or None
        confirm = bool(body.pop("confirm", False))
        try:
            result = verbs_mod.run(repo_root, verb_id, ticket=ticket,
                                   confirm=confirm, args=body)
        except Exception as exc:
            # Recorded either way: a refused run is exactly the kind of thing
            # you want in the trail when you are working out what happened.
            audit.record(repo_root, "verb.run", actor=audit.actor_of(req),
                         target=verb_id, detail={"ticket": ticket or ""},
                         outcome="error: %s" % exc)
            raise
        audit.record(repo_root, "verb.run", actor=audit.actor_of(req),
                     target=verb_id, detail={"ticket": ticket or ""})
        return {"verb": verb_id, "result": result}

    def submit(req, verb_id):
        """Queue a verb instead of running it inline.

        For anything slow enough that a browser request would time out waiting.
        The queue is the same one the scheduler uses, so a job started here is
        visible and cancellable like any other.
        """
        body = dict(req.body or {})
        ticket = body.pop("ticket", None) or None
        confirm = bool(body.pop("confirm", False))
        queue = jobs_mod.JobQueue(repo_root).start()
        job = queue.submit(verb_id, ticket=ticket, confirm=confirm, args=body,
                           submitted_by="console")
        audit.record(repo_root, "verb.submit", actor=audit.actor_of(req),
                     target=verb_id,
                     detail={"ticket": ticket or "", "job": job["id"]})
        return job

    def job_listing(req):
        return {"jobs": jobs_mod.JobQueue(repo_root).list_jobs(
            state=req.query.get("state"), ticket=req.query.get("ticket"))}

    def job_cancel(req, job_id):
        """Cancel a QUEUED job. A running one is refused, not faked.

        Stopping work mid-flight needs the worker's cooperation and a handler
        that can be interrupted safely. Reporting "cancelled" while the job
        carries on would be worse than saying no.
        """
        try:
            job = jobs_mod.JobQueue(repo_root).cancel(job_id)
        except Exception as exc:
            # A refused cancel belongs in the trail as much as a granted one:
            # "I tried to stop it and could not" is the fact you want later.
            audit.record(repo_root, "job.cancel", actor=audit.actor_of(req),
                         target=job_id, outcome="refused: %s" % exc)
            raise
        audit.record(repo_root, "job.cancel", actor=audit.actor_of(req),
                     target=job_id)
        return job

    ctx.get(r"^/api/verbs/?$", listing, "verbs.list")
    ctx.post(r"^/api/verbs/([A-Za-z0-9_-]+)/run/?$", run, "verbs.run")
    ctx.post(r"^/api/verbs/([A-Za-z0-9_-]+)/submit/?$", submit, "verbs.submit")
    ctx.get(r"^/api/jobs/?$", job_listing, "verbs.jobs")
    ctx.post(r"^/api/jobs/([A-Za-z0-9]+)/cancel/?$", job_cancel, "verbs.job_cancel")


PLUGIN = Plugin(
    id="verbs",
    apply=apply,
    requires=("boards",),
    summary="Deterministic jobs the console can run without a model.",
)
