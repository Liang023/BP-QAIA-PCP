\ Model master
\ LP format - for model browsing. Use MPS format to capture full model detail.
Minimize
  T + 1000 column_1 + 1000 column_2
Subject To
 each_partition_colored_once_constraint0: column_1 + column_3 + column_59
   + column_60 + column_61 + column_62 + column_63 + column_64 + column_65
   + column_3515 + column_3516 + column_3517 + column_3518 + column_3519
   + column_3520 + column_3521 + column_3522 + column_3523 >= 1
 each_partition_colored_once_constraint1: column_2 + column_3 + column_61
   + column_63 + column_64 + column_65 + column_3517 + column_3518
   + column_3520 + column_3521 + column_3522 + column_3523 >= 1
 each_partition_colored_once_constraint2: column_1 + column_3 + column_18
   + column_63 + column_3512 + column_3513 + column_3515 + column_3516
   + column_3517 + column_3518 + column_3519 + column_3520 + column_3521
   + column_3522 + column_3523 >= 1
 each_partition_colored_once_constraint3: column_2 + column_3 + column_26
   + column_27 + column_28 + column_29 + column_30 + column_31 + column_32
   + column_33 + column_34 + column_35 + column_96 >= 1
 each_partition_colored_once_constraint4: column_1 + column_26 + column_27
   + column_28 + column_29 + column_30 + column_31 + column_32 + column_33
   + column_34 + column_35 >= 1
 each_partition_colored_once_constraint5: column_2 + column_18 + column_26
   + column_27 + column_28 + column_29 + column_30 + column_31 + column_32
   + column_33 + column_34 + column_35 + column_46 + column_47 + column_48
   + column_49 + column_50 + column_51 + column_52 + column_53 + column_54
   + column_55 + column_57 + column_58 + column_59 + column_60 + column_61
   + column_62 + column_63 + column_64 + column_65 >= 1
 each_partition_colored_once_constraint6: column_1 + column_46 + column_47
   + column_48 + column_49 + column_50 + column_51 + column_52 + column_53
   + column_54 + column_55 + column_57 + column_58 + column_59 + column_60
   + column_61 + column_62 + column_63 + column_64 + column_65 + column_96
   >= 1
 each_partition_colored_once_constraint7: column_2 + column_3 + column_46
   + column_47 + column_48 + column_49 + column_50 + column_51 + column_52
   + column_53 + column_54 + column_55 + column_57 + column_58 + column_59
   + column_60 + column_61 + column_62 + column_63 + column_64 + column_65
   + column_96 >= 1
 each_partition_colored_once_constraint8: column_1 + column_5 + column_18
   + column_26 + column_27 + column_28 + column_29 + column_30 + column_31
   + column_32 + column_33 + column_34 + column_35 + column_46 + column_47
   + column_48 + column_49 + column_50 + column_51 + column_52 + column_53
   + column_54 + column_55 + column_57 + column_58 + column_59 + column_60
   + column_61 + column_62 + column_63 + column_64 + column_65 >= 1
 each_partition_colored_once_constraint9: column_2 + column_3 + column_18
   + column_58 + column_59 + column_60 + column_61 + column_62 + column_63
   >= 1
 makespan_vertex_0: T - column_1 - column_3 - column_59 - column_61
   - column_63 - column_65 - column_3515 - column_3517 - column_3518
   - column_3521 - column_3523 >= 0
 makespan_vertex_1: T - 2 column_60 - 2 column_64 - 2 column_3516
   - 2 column_3520 - 2 column_3522 >= 0
 makespan_vertex_2: T - column_62 - column_3519 >= 0
 makespan_vertex_3: T >= 0
 makespan_vertex_4: T - 2 column_2 - 2 column_3 - 2 column_61 - 2 column_63
   - 2 column_3517 - 2 column_3518 >= 0
 makespan_vertex_5: T - 4 column_64 - 4 column_65 - 4 column_3520
   - 4 column_3521 - 4 column_3522 - 4 column_3523 >= 0
 makespan_vertex_6: T >= 0
 makespan_vertex_7: T - 3 column_1 - 3 column_3 - 3 column_18 - 3 column_63
   - 3 column_3512 - 3 column_3515 - 3 column_3516 - 3 column_3517
   - 3 column_3519 - 3 column_3520 - 3 column_3521 >= 0
 makespan_vertex_8: T - 12 column_3513 - 12 column_3518 - 12 column_3522
   - 12 column_3523 >= 0
 makespan_vertex_9: T - 4 column_2 - 4 column_3 - 4 column_26 - 4 column_27
   - 4 column_28 - 4 column_29 - 4 column_30 - 4 column_31 - 4 column_32
   - 4 column_33 - 4 column_34 - 4 column_35 - 4 column_96 >= 0
 makespan_vertex_10: T >= 0
 makespan_vertex_11: T - 5 column_1 - 5 column_26 - 5 column_27
   - 5 column_28 - 5 column_29 - 5 column_30 - 5 column_31 >= 0
 makespan_vertex_12: T >= 0
 makespan_vertex_13: T >= 0
 makespan_vertex_14: T - 10 column_32 - 10 column_33 - 10 column_34
   - 10 column_35 >= 0
 makespan_vertex_15: T - 6 column_2 - 6 column_18 - 6 column_26
   - 6 column_27 - 6 column_32 - 6 column_46 - 6 column_47 - 6 column_48
   - 6 column_49 - 6 column_57 - 6 column_59 - 6 column_61 - 6 column_62
   - 6 column_63 - 6 column_65 >= 0
 makespan_vertex_16: T - column_28 - column_29 - column_33 - column_34
   - column_50 - column_51 - column_52 - column_53 - column_58 - column_60
   - column_64 >= 0
 makespan_vertex_17: T - column_30 - column_31 - column_35 - column_54
   - column_55 >= 0
 makespan_vertex_18: T - 7 column_1 - 7 column_46 - 7 column_47
   - 7 column_50 - 7 column_51 - 7 column_54 - 7 column_55 - 7 column_57
   - 7 column_58 - 7 column_59 - 7 column_60 - 7 column_61 - 7 column_62
   - 7 column_63 - 7 column_64 - 7 column_65 - 7 column_96 >= 0
 makespan_vertex_19: T - 4 column_48 - 4 column_49 - 4 column_52
   - 4 column_53 >= 0
 makespan_vertex_20: T - 8 column_2 - 8 column_3 - 8 column_46
   - 8 column_47 - 8 column_48 - 8 column_49 - 8 column_50 - 8 column_51
   - 8 column_52 - 8 column_53 - 8 column_54 - 8 column_55 - 8 column_57
   - 8 column_58 - 8 column_59 - 8 column_60 - 8 column_61 - 8 column_62
   - 8 column_63 - 8 column_64 - 8 column_65 >= 0
 makespan_vertex_21: T - 9 column_96 >= 0
 makespan_vertex_22: T - 9 column_1 - 9 column_26 - 9 column_28
   - 9 column_30 - 9 column_33 - 9 column_35 - 9 column_46 - 9 column_48
   - 9 column_50 - 9 column_52 - 9 column_54 - 9 column_64 - 9 column_65
   >= 0
 makespan_vertex_23: T - column_5 >= 0
 makespan_vertex_24: T - 9 column_27 - 9 column_29 - 9 column_31
   - 9 column_32 - 9 column_34 - 9 column_47 - 9 column_49 - 9 column_51
   - 9 column_53 - 9 column_55 >= 0
 makespan_vertex_25: T - 4 column_18 - 4 column_57 - 4 column_58
   - 4 column_59 - 4 column_60 - 4 column_61 - 4 column_62 - 4 column_63
   >= 0
 makespan_vertex_26: T - 10 column_2 >= 0
 makespan_vertex_27: T >= 0
 makespan_vertex_28: T >= 0
 makespan_vertex_29: T - 9 column_3 - 9 column_18 - 9 column_58
   - 9 column_59 - 9 column_60 - 9 column_61 - 9 column_62 - 9 column_63
   >= 0
 charger_capacity_constraint: column_1 + column_2 + column_3 + column_5
   + column_18 + column_26 + column_27 + column_28 + column_29 + column_30
   + column_31 + column_32 + column_33 + column_34 + column_35 + column_46
   + column_47 + column_48 + column_49 + column_50 + column_51 + column_52
   + column_53 + column_54 + column_55 + column_57 + column_58 + column_59
   + column_60 + column_61 + column_62 + column_63 + column_64 + column_65
   + column_96 + column_3512 + column_3513 + column_3515 + column_3516
   + column_3517 + column_3518 + column_3519 + column_3520 + column_3521
   + column_3522 + column_3523 <= 2
Bounds
End
