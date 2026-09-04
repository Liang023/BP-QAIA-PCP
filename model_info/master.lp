\ Model master
\ LP format - for model browsing. Use MPS format to capture full model detail.
Minimize
  T + 1000 column_1 + 1000 column_2
Subject To
 each_partition_colored_once_constraint0: column_1 + column_38 + column_42
   + column_50 + column_54 + column_79 + column_80 + column_83 + column_85
   + column_88 + column_91 + column_99 + column_103 + column_118
   + column_125 + column_1058 + column_1060 + column_1062 + column_1063
   + column_1066 + column_1071 + column_1107 + column_1109 + column_1111
   + column_1113 + column_1115 + column_1147 + column_1150 + column_1152
   + column_1153 + column_1155 + column_1159 + column_1162 + column_1163
   + column_1164 >= 1
 each_partition_colored_once_constraint1: column_2 + column_42 + column_54
   + column_80 + column_81 + column_83 + column_85 + column_90 + column_103
   + column_1060 + column_1061 + column_1062 + column_1063 + column_1064
   + column_1065 + column_1108 + column_1109 + column_1110 + column_1111
   + column_1112 + column_1113 + column_1114 + column_1115 + column_1148
   + column_1149 + column_1160 + column_1161 >= 1
 each_partition_colored_once_constraint2: column_1 + column_83 + column_91
   + column_95 + column_125 + column_1062 + column_1065 + column_1070
   + column_1071 + column_1111 + column_1112 + column_1115 + column_1149
   + column_1150 + column_1151 + column_1152 + column_1161 + column_1162
   + column_1164 + column_1165 >= 1
 each_partition_colored_once_constraint3: column_2 + column_87 + column_88
   + column_90 + column_91 + column_95 + column_116 + column_118
   + column_125 + column_1066 + column_1067 + column_1068 + column_1069
   + column_1070 + column_1071 + column_1158 + column_1159 + column_1160
   + column_1161 + column_1162 + column_1165 >= 1
 each_partition_colored_once_constraint4: column_1 + column_1057
   + column_1059 + column_1061 + column_1064 + column_1065 + column_1067
   + column_1068 + column_1069 + column_1070 + column_1154 >= 1
 each_partition_colored_once_constraint5: column_2 + column_78 + column_79
   + column_80 + column_81 + column_83 + column_85 + column_1066
   + column_1067 + column_1068 + column_1069 + column_1070 + column_1071
   + column_1106 + column_1107 + column_1108 + column_1109 + column_1110
   + column_1111 + column_1112 + column_1113 + column_1114 + column_1115
   + column_1152 + column_1153 + column_1155 >= 1
 each_partition_colored_once_constraint6: column_1 + column_87 + column_88
   + column_90 + column_91 + column_95 + column_1057 + column_1058
   + column_1059 + column_1060 + column_1061 + column_1062 + column_1063
   + column_1064 + column_1065 + column_1068 + column_1146 + column_1147
   + column_1148 + column_1149 + column_1150 + column_1151 + column_1152
   + column_1153 + column_1154 + column_1155 + column_1156 + column_1163
   + column_1164 >= 1
 each_partition_colored_once_constraint7: column_2 + column_36 + column_38
   + column_42 + column_46 + column_97 + column_99 + column_103
   + column_1057 + column_1058 + column_1059 + column_1060 + column_1061
   + column_1062 + column_1063 + column_1064 + column_1065 + column_1066
   + column_1067 + column_1068 + column_1069 + column_1070 + column_1071
   + column_1155 >= 1
 each_partition_colored_once_constraint8: column_1 + column_5 + column_78
   + column_79 + column_80 + column_81 + column_83 + column_85 + column_87
   + column_88 + column_90 + column_91 + column_95 + column_1068 >= 1
 each_partition_colored_once_constraint9: column_2 + column_46 + column_48
   + column_50 + column_54 + column_78 + column_79 + column_80 + column_81
   + column_83 + column_85 + column_1057 + column_1058 + column_1059
   + column_1060 + column_1061 + column_1062 + column_1063 + column_1064
   + column_1065 + column_1156 + column_1158 + column_1159 + column_1160
   + column_1161 + column_1162 + column_1163 + column_1164 + column_1165
   >= 1
 makespan_vertex_0: T - column_1 >= 0
 makespan_vertex_1: T - 2 column_38 - 2 column_42 - 2 column_50
   - 2 column_54 - 2 column_79 - 2 column_80 - 2 column_83 - 2 column_85
   - 2 column_88 - 2 column_91 - 2 column_99 - 2 column_103 - 2 column_118
   - 2 column_125 - 2 column_1058 - 2 column_1060 - 2 column_1062
   - 2 column_1063 - 2 column_1066 - 2 column_1071 - 2 column_1107
   - 2 column_1109 - 2 column_1111 - 2 column_1113 - 2 column_1115
   - 2 column_1147 - 2 column_1150 - 2 column_1152 - 2 column_1153
   - 2 column_1155 - 2 column_1159 - 2 column_1162 - 2 column_1163
   - 2 column_1164 >= 0
 makespan_vertex_2: T >= 0
 makespan_vertex_3: T >= 0
 makespan_vertex_4: T - 2 column_2 - 2 column_81 - 2 column_90
   - 2 column_1108 - 2 column_1112 - 2 column_1148 - 2 column_1149
   - 2 column_1160 - 2 column_1161 >= 0
 makespan_vertex_5: T - 4 column_42 - 4 column_54 - 4 column_80
   - 4 column_83 - 4 column_103 - 4 column_1060 - 4 column_1061
   - 4 column_1062 - 4 column_1065 - 4 column_1109 - 4 column_1110
   - 4 column_1111 >= 0
 makespan_vertex_6: T - 4 column_85 - 4 column_1063 - 4 column_1064
   - 4 column_1113 - 4 column_1114 - 4 column_1115 >= 0
 makespan_vertex_7: T - 3 column_1 - 3 column_83 - 3 column_91
   - 3 column_95 - 3 column_125 - 3 column_1062 - 3 column_1065
   - 3 column_1070 - 3 column_1071 - 3 column_1111 - 3 column_1112
   - 3 column_1115 - 3 column_1149 - 3 column_1150 - 3 column_1151
   - 3 column_1152 - 3 column_1161 - 3 column_1162 - 3 column_1164
   - 3 column_1165 >= 0
 makespan_vertex_8: T >= 0
 makespan_vertex_9: T - 4 column_2 - 4 column_87 - 4 column_88
   - 4 column_90 - 4 column_91 - 4 column_95 - 4 column_116 - 4 column_118
   - 4 column_125 - 4 column_1066 - 4 column_1067 - 4 column_1068
   - 4 column_1069 - 4 column_1070 - 4 column_1071 - 4 column_1158
   - 4 column_1159 - 4 column_1160 - 4 column_1161 - 4 column_1162
   - 4 column_1165 >= 0
 makespan_vertex_10: T >= 0
 makespan_vertex_11: T - 5 column_1 >= 0
 makespan_vertex_12: T >= 0
 makespan_vertex_13: T - 2 column_1057 - 2 column_1059 - 2 column_1061
   - 2 column_1064 - 2 column_1065 - 2 column_1067 - 2 column_1068
   - 2 column_1069 - 2 column_1070 - 2 column_1154 >= 0
 makespan_vertex_14: T >= 0
 makespan_vertex_15: T - 6 column_2 - 6 column_78 - 6 column_79
   - 6 column_80 - 6 column_81 - 6 column_83 - 6 column_85 - 6 column_1066
   - 6 column_1067 - 6 column_1068 - 6 column_1069 - 6 column_1070
   - 6 column_1071 - 6 column_1152 - 6 column_1153 - 6 column_1155 >= 0
 makespan_vertex_16: T >= 0
 makespan_vertex_17: T - column_1106 - column_1107 - column_1108
   - column_1109 - column_1110 - column_1111 - column_1112 - column_1113
   - column_1114 - column_1115 >= 0
 makespan_vertex_18: T - 7 column_1 - 7 column_87 - 7 column_88
   - 7 column_90 - 7 column_91 - 7 column_95 - 7 column_1057
   - 7 column_1058 - 7 column_1059 - 7 column_1060 - 7 column_1061
   - 7 column_1062 - 7 column_1063 - 7 column_1064 - 7 column_1065
   - 7 column_1068 >= 0
 makespan_vertex_19: T - 4 column_1146 - 4 column_1147 - 4 column_1148
   - 4 column_1149 - 4 column_1150 - 4 column_1151 - 4 column_1152
   - 4 column_1153 - 4 column_1154 - 4 column_1155 - 4 column_1156
   - 4 column_1163 - 4 column_1164 >= 0
 makespan_vertex_20: T - 8 column_2 - 8 column_97 - 8 column_99
   - 8 column_103 - 8 column_1058 - 8 column_1059 - 8 column_1060
   - 8 column_1061 - 8 column_1062 - 8 column_1063 - 8 column_1064
   - 8 column_1065 - 8 column_1066 - 8 column_1067 - 8 column_1068
   - 8 column_1070 - 8 column_1071 - 8 column_1155 >= 0
 makespan_vertex_21: T - 9 column_36 - 9 column_38 - 9 column_42
   - 9 column_46 - 9 column_1057 - 9 column_1069 >= 0
 makespan_vertex_22: T - 9 column_1 >= 0
 makespan_vertex_23: T - column_5 - column_78 - column_79 - column_80
   - column_81 - column_83 - column_85 - column_87 - column_88 - column_90
   - column_91 - column_95 - column_1068 >= 0
 makespan_vertex_24: T >= 0
 makespan_vertex_25: T >= 0
 makespan_vertex_26: T - 10 column_2 - 10 column_46 - 10 column_48
   - 10 column_50 - 10 column_54 - 10 column_78 - 10 column_79
   - 10 column_80 - 10 column_81 - 10 column_83 - 10 column_85
   - 10 column_1057 - 10 column_1058 - 10 column_1059 - 10 column_1060
   - 10 column_1061 - 10 column_1062 - 10 column_1063 - 10 column_1064
   - 10 column_1065 - 10 column_1156 - 10 column_1158 - 10 column_1159
   - 10 column_1160 - 10 column_1161 - 10 column_1162 - 10 column_1163
   - 10 column_1164 - 10 column_1165 >= 0
 makespan_vertex_27: T >= 0
 makespan_vertex_28: T >= 0
 makespan_vertex_29: T >= 0
 charger_capacity_constraint: column_1 + column_2 + column_5 + column_36
   + column_38 + column_42 + column_46 + column_48 + column_50 + column_54
   + column_78 + column_79 + column_80 + column_81 + column_83 + column_85
   + column_87 + column_88 + column_90 + column_91 + column_95 + column_97
   + column_99 + column_103 + column_116 + column_118 + column_125
   + column_1057 + column_1058 + column_1059 + column_1060 + column_1061
   + column_1062 + column_1063 + column_1064 + column_1065 + column_1066
   + column_1067 + column_1068 + column_1069 + column_1070 + column_1071
   + column_1106 + column_1107 + column_1108 + column_1109 + column_1110
   + column_1111 + column_1112 + column_1113 + column_1114 + column_1115
   + column_1146 + column_1147 + column_1148 + column_1149 + column_1150
   + column_1151 + column_1152 + column_1153 + column_1154 + column_1155
   + column_1156 + column_1158 + column_1159 + column_1160 + column_1161
   + column_1162 + column_1163 + column_1164 + column_1165 <= 2
Bounds
End
