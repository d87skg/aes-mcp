// AEF Drift Detection — Rust 侧类型定义
// 文件: agent-core/src/drift/types.rs
// 与 Python drift_engine.py 的输出格式完全对齐

use serde::{Deserialize, Serialize};

/// 漂移类别枚举
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum DriftCategory {
    ContextDrift,    // 上下文窗口污染
    GoalDrift,       // 目标函数偏移
    ToolDrift,       // 工具调用异常
    ConstraintDrift, // 显式约束滑落
    Unknown,
}

/// 单个约束定义
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Constraint {
    pub id: String,
    pub description: String,
    pub category: String,
    pub check_type: String,
    pub rule: String,
    pub severity: String,
    pub auto_meltdown: bool,
}

/// 约束丢失事件
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConstraintLostEvent {
    pub step: u32,
    pub timestamp: String,
    #[serde(rename = "type")]
    pub event_type: String,             // "constraint_lost"
    pub constraint_id: String,
    pub constraint_desc: String,
    pub severity: String,
    pub drift_category: DriftCategory,
    pub auto_meltdown: bool,
    pub suspected_cause: String,
    pub pollution_source: String,
}

/// 执行失败事件
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionFailureEvent {
    pub step: u32,
    pub timestamp: String,
    #[serde(rename = "type")]
    pub event_type: String,             // "execution_failure"
    pub status: String,
    pub severity: String,
    pub financial_loss: String,
    pub liquidation_price: String,
}

/// 统一漂移事件枚举
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum DriftEvent {
    #[serde(rename = "constraint_lost")]
    ConstraintLost(ConstraintLostEvent),
    #[serde(rename = "execution_failure")]
    ExecutionFailure(ExecutionFailureEvent),
}

/// 因果链节点
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CausalityNode {
    pub trigger_step: u32,
    pub event_type: String,
    pub drift_category: String,
    pub detail: String,
    pub caused_by: String,
    pub resulted_in: String,
}

/// 漂移检测报告
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DriftReport {
    pub engine_version: String,
    pub trace_id: String,
    pub total_steps: u32,
    pub drift_detected: bool,
    pub drift_events: Vec<DriftEvent>,
    pub causality_chain: Vec<CausalityNode>,
    pub summary: DriftSummary,
}

/// 报告摘要
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DriftSummary {
    pub root_cause: String,
    pub impact: String,
    pub preventable: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub meltdown_recommended: Option<bool>,
}

/// agent-core 对外暴露的核心 trait
pub trait DriftDetector {
    /// 输入两步的快照，返回漂移事件列表
    fn detect(
        &self,
        step_num: u32,
        timestamp: &str,
        prev_constraints: &[String],
        curr_constraints: &[String],
        prev_tool: &str,
        curr_tool: &str,
        curr_observations: &[String],
    ) -> Vec<DriftEvent>;

    /// 加载 YAML 约束配置
    fn load_constraints(&mut self, yaml_path: &str) -> Result<(), String>;

    /// 获取当前活跃约束列表
    fn active_constraints(&self) -> &[Constraint];
}
