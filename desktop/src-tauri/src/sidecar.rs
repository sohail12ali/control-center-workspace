use serde::Deserialize;
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

#[derive(Debug, Deserialize, Clone)]
pub struct Handle {
    pub url: String,
    pub owned: bool,
    pub pid: Option<u32>,
}

#[derive(Debug)]
pub struct SidecarError(pub String);

impl std::fmt::Display for SidecarError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}

impl std::error::Error for SidecarError {}

fn is_root(path: &Path) -> bool {
    path.join("console").join("kanban.py").is_file() && path.join("knowledge-center").is_dir()
}

fn walk_up(start: PathBuf) -> Option<PathBuf> {
    let mut path = start;
    loop {
        if is_root(&path) {
            return Some(path);
        }
        if !path.pop() {
            return None;
        }
    }
}

pub fn find_repo_root() -> Result<PathBuf, SidecarError> {
    let mut starts: Vec<PathBuf> = Vec::new();
    if let Ok(cwd) = std::env::current_dir() {
        starts.push(cwd);
    }
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            starts.push(dir.to_path_buf());
        }
    }
    for start in starts {
        if let Some(root) = walk_up(start) {
            return Ok(root);
        }
    }
    Err(SidecarError(
        "no workspace root found (need knowledge-center/ and console/kanban.py)".into(),
    ))
}

fn python_cmd() -> String {
    if let Ok(env) = std::env::var("PYTHON") {
        if !env.trim().is_empty() {
            return env;
        }
    }
    if cfg!(windows) {
        "python".into()
    } else {
        "python3".into()
    }
}

fn python_command() -> Command {
    let mut cmd = Command::new(python_cmd());
    cmd.arg("-u");
    cmd.env("PYTHONUNBUFFERED", "1");
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x0800_0000); // CREATE_NO_WINDOW
    }
    cmd
}

fn sidecar_py(root: &Path) -> PathBuf {
    root.join("desktop").join("sidecar.py")
}

/// `extra_env` is unused by T-003 itself — plumbing for T-005's native
/// bridge, which needs to hand the sidecar a token via the environment
/// rather than an argv anyone with `ps`/Task Manager could read.
pub fn ensure(root: &Path, extra_env: &HashMap<String, String>) -> Result<Handle, SidecarError> {
    let script = sidecar_py(root);
    if !script.is_file() {
        return Err(SidecarError(format!("missing {}", script.display())));
    }
    let mut cmd = python_command();
    cmd.arg(&script)
        .arg("ensure")
        .arg("--root")
        .arg(root)
        .current_dir(root)
        .envs(extra_env)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    let output = cmd
        .output()
        .map_err(|e| SidecarError(format!("could not run sidecar ensure: {e}")))?;
    if !output.status.success() {
        let err = String::from_utf8_lossy(&output.stderr);
        let out = String::from_utf8_lossy(&output.stdout);
        let msg = if !err.trim().is_empty() {
            err.trim().to_string()
        } else {
            out.trim().to_string()
        };
        return Err(SidecarError(if msg.is_empty() {
            format!("sidecar ensure failed ({})", output.status)
        } else {
            msg
        }));
    }
    serde_json::from_slice(&output.stdout)
        .map_err(|e| SidecarError(format!("sidecar ensure returned invalid JSON: {e}")))
}

pub fn stop(root: &Path, pid: u32) {
    let script = sidecar_py(root);
    let _ = python_command()
        .arg(script)
        .arg("stop")
        .arg("--pid")
        .arg(pid.to_string())
        .current_dir(root)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status();
}
