import Lake
open Lake DSL

package «ef_cake5» where
  moreLeanArgs := #["-j", "1"]

@[default_target]
lean_lib «EnvyFreeCake5» where
