\ Model master
\ LP format - for model browsing. Use MPS format to capture full model detail.
Minimize
  T + 1000 column_1 + 1000 column_2
Subject To
 each_partition_colored_once_constraint0: column_1 + column_38 + column_40
   + column_42 + column_68 + column_69 + column_72 + column_75 + column_88
   + column_94 + column_99 + column_101 + column_103 + column_109
   + column_110 + column_113 + column_3117 + column_3118 + column_3120
   + column_3167 + column_3168 + column_3170 + column_3175 + column_3207
   + column_3210 + column_3211 + column_3212 >= 1
 each_partition_colored_once_constraint1: column_2 + column_42 + column_66
   + column_67 + column_68 + column_69 + column_70 + column_72 + column_75
   + column_90 + column_103 + column_106 + column_107 + column_108
   + column_109 + column_110 + column_111 + column_113 + column_3120
   + column_3121 + column_3169 + column_3170 + column_3208 + column_3214
   + column_3215 >= 1
 each_partition_colored_once_constraint2: column_1 + column_72 + column_94
   + column_113 + column_3175 + column_3211 + column_3212 + column_3213
   + column_3214 >= 1
 each_partition_colored_once_constraint3: column_2 + column_87 + column_88
   + column_90 + column_94 + column_3116 + column_3117 + column_3118
   + column_3120 + column_3121 + column_3166 + column_3167 + column_3168
   + column_3169 + column_3170 + column_3175 + column_3206 + column_3207
   + column_3208 + column_3209 + column_3210 + column_3211 + column_3212
   + column_3213 + column_3214 + column_3215 >= 1
 each_partition_colored_once_constraint4: column_1 + column_4 + column_66
   + column_67 + column_68 + column_69 + column_70 + column_72 + column_75
   + column_106 + column_107 + column_108 + column_109 + column_110
   + column_111 + column_113 + column_3206 + column_3207 + column_3208
   + column_3209 + column_3210 + column_3211 + column_3212 + column_3213
   + column_3214 + column_3215 >= 1
 each_partition_colored_once_constraint5: column_2 + column_4 + column_77
   + column_106 + column_107 + column_108 + column_109 + column_110
   + column_111 + column_113 + column_3116 + column_3117 + column_3118
   + column_3120 + column_3121 >= 1
 each_partition_colored_once_constraint6: column_1 + column_4 + column_87
   + column_88 + column_90 + column_94 + column_106 + column_107
   + column_108 + column_109 + column_110 + column_111 + column_113
   + column_3206 + column_3207 + column_3208 + column_3209 + column_3210
   + column_3211 + column_3212 + column_3213 + column_3214 + column_3215
   >= 1
 each_partition_colored_once_constraint7: column_2 + column_36 + column_38
   + column_40 + column_42 + column_97 + column_99 + column_101
   + column_103 + column_3116 + column_3117 + column_3118 + column_3120
   + column_3121 + column_3166 + column_3167 + column_3168 + column_3169
   + column_3170 + column_3175 + column_3206 + column_3207 + column_3208
   + column_3209 + column_3210 + column_3211 + column_3212 + column_3213
   + column_3214 + column_3215 >= 1
 each_partition_colored_once_constraint8: column_1 + column_5 + column_66
   + column_67 + column_68 + column_69 + column_70 + column_72 + column_75
   + column_77 + column_87 + column_88 + column_90 + column_94 + column_106
   + column_107 + column_108 + column_109 + column_110 + column_111
   + column_113 + column_3206 + column_3207 + column_3208 + column_3209
   + column_3210 + column_3211 + column_3212 + column_3213 + column_3214
   + column_3215 >= 1
 each_partition_colored_once_constraint9: column_2 + column_77 + column_106
   + column_107 + column_108 + column_109 + column_110 + column_111
   + column_113 + column_3166 + column_3167 + column_3168 + column_3169
   + column_3170 + column_3175 >= 1
 makespan_vertex_0: T - column_1 >= 0
 makespan_vertex_1: T - 2 column_38 - 2 column_42 - 2 column_68
   - 2 column_69 - 2 column_72 - 2 column_75 - 2 column_88 - 2 column_94
   - 2 column_99 - 2 column_103 - 2 column_109 - 2 column_110
   - 2 column_113 - 2 column_3117 - 2 column_3167 - 2 column_3175
   - 2 column_3207 - 2 column_3210 - 2 column_3211 - 2 column_3212 >= 0
 makespan_vertex_2: T - column_40 - column_101 - column_3118 - column_3120
   - column_3168 - column_3170 >= 0
 makespan_vertex_3: T >= 0
 makespan_vertex_4: T - 2 column_2 - 2 column_66 - 2 column_90
   - 2 column_106 - 2 column_107 - 2 column_3120 - 2 column_3121
   - 2 column_3169 - 2 column_3170 - 2 column_3208 - 2 column_3214
   - 2 column_3215 >= 0
 makespan_vertex_5: T - 4 column_42 - 4 column_67 - 4 column_68
   - 4 column_72 - 4 column_75 - 4 column_103 - 4 column_108 - 4 column_109
   - 4 column_113 >= 0
 makespan_vertex_6: T - 4 column_69 - 4 column_70 - 4 column_110
   - 4 column_111 >= 0
 makespan_vertex_7: T - 3 column_1 - 3 column_72 - 3 column_113 >= 0
 makespan_vertex_8: T - 12 column_94 - 12 column_3175 - 12 column_3211
   - 12 column_3212 - 12 column_3213 - 12 column_3214 >= 0
 makespan_vertex_9: T - 4 column_2 - 4 column_87 - 4 column_88
   - 4 column_90 - 4 column_94 - 4 column_3116 - 4 column_3117
   - 4 column_3118 - 4 column_3120 - 4 column_3121 - 4 column_3166
   - 4 column_3167 - 4 column_3168 - 4 column_3169 - 4 column_3170
   - 4 column_3175 - 4 column_3206 - 4 column_3207 - 4 column_3208
   - 4 column_3209 - 4 column_3210 - 4 column_3211 - 4 column_3212
   - 4 column_3213 - 4 column_3214 - 4 column_3215 >= 0
 makespan_vertex_10: T >= 0
 makespan_vertex_11: T - 5 column_1 - 5 column_66 - 5 column_67
   - 5 column_68 - 5 column_69 - 5 column_70 - 5 column_72 - 5 column_106
   - 5 column_108 - 5 column_109 - 5 column_110 - 5 column_111
   - 5 column_113 - 5 column_3206 - 5 column_3207 - 5 column_3208
   - 5 column_3211 - 5 column_3213 - 5 column_3214 >= 0
 makespan_vertex_12: T - 9 column_75 >= 0
 makespan_vertex_13: T - 2 column_4 >= 0
 makespan_vertex_14: T - 10 column_107 - 10 column_3209 - 10 column_3210
   - 10 column_3212 - 10 column_3215 >= 0
 makespan_vertex_15: T - 6 column_2 - 6 column_77 - 6 column_106
   - 6 column_107 - 6 column_108 - 6 column_109 - 6 column_110
   - 6 column_111 - 6 column_113 - 6 column_3116 - 6 column_3117
   - 6 column_3118 - 6 column_3120 - 6 column_3121 >= 0
 makespan_vertex_16: T - column_4 >= 0
 makespan_vertex_17: T >= 0
 makespan_vertex_18: T - 7 column_1 - 7 column_87 - 7 column_88
   - 7 column_90 - 7 column_94 - 7 column_106 - 7 column_107 - 7 column_108
   - 7 column_109 - 7 column_110 - 7 column_111 - 7 column_113
   - 7 column_3206 - 7 column_3207 - 7 column_3208 - 7 column_3209
   - 7 column_3210 - 7 column_3211 - 7 column_3212 - 7 column_3213
   - 7 column_3214 - 7 column_3215 >= 0
 makespan_vertex_19: T - 4 column_4 >= 0
 makespan_vertex_20: T - 8 column_2 - 8 column_97 - 8 column_99
   - 8 column_101 - 8 column_103 - 8 column_3116 - 8 column_3117
   - 8 column_3118 - 8 column_3120 - 8 column_3121 - 8 column_3166
   - 8 column_3167 - 8 column_3168 - 8 column_3169 - 8 column_3170
   - 8 column_3175 - 8 column_3206 - 8 column_3207 - 8 column_3208
   - 8 column_3209 - 8 column_3210 - 8 column_3211 - 8 column_3212
   - 8 column_3213 - 8 column_3214 - 8 column_3215 >= 0
 makespan_vertex_21: T - 9 column_36 - 9 column_38 - 9 column_40
   - 9 column_42 >= 0
 makespan_vertex_22: T - 9 column_1 >= 0
 makespan_vertex_23: T - column_5 - column_66 - column_67 - column_68
   - column_69 - column_70 - column_72 - column_75 - column_77 - column_87
   - column_88 - column_90 - column_94 - column_106 - column_107
   - column_108 - column_109 - column_110 - column_111 - column_113
   - column_3206 - column_3207 - column_3208 - column_3209 - column_3210
   - column_3211 - column_3212 - column_3213 - column_3214 - column_3215
   >= 0
 makespan_vertex_24: T >= 0
 makespan_vertex_25: T >= 0
 makespan_vertex_26: T - 10 column_2 >= 0
 makespan_vertex_27: T >= 0
 makespan_vertex_28: T >= 0
 makespan_vertex_29: T - 9 column_77 - 9 column_106 - 9 column_107
   - 9 column_108 - 9 column_109 - 9 column_110 - 9 column_111
   - 9 column_113 - 9 column_3166 - 9 column_3167 - 9 column_3168
   - 9 column_3169 - 9 column_3170 - 9 column_3175 >= 0
 charger_capacity_constraint: column_1 + column_2 + column_4 + column_5
   + column_36 + column_38 + column_40 + column_42 + column_66 + column_67
   + column_68 + column_69 + column_70 + column_72 + column_75 + column_77
   + column_87 + column_88 + column_90 + column_94 + column_97 + column_99
   + column_101 + column_103 + column_106 + column_107 + column_108
   + column_109 + column_110 + column_111 + column_113 + column_3116
   + column_3117 + column_3118 + column_3120 + column_3121 + column_3166
   + column_3167 + column_3168 + column_3169 + column_3170 + column_3175
   + column_3206 + column_3207 + column_3208 + column_3209 + column_3210
   + column_3211 + column_3212 + column_3213 + column_3214 + column_3215
   <= 2
Bounds
End
