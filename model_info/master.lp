\ Model master
\ LP format - for model browsing. Use MPS format to capture full model detail.
Minimize
  T + 1000 column_1 + 1000 column_2 + 1000 column_3 + 1000 column_4
Subject To
 each_partition_colored_once_constraint0: column_1 + column_63 + column_65
   + column_83 + column_85 + column_93 + column_95 + column_172
   + column_174 + column_253 + column_255 + column_966 + column_967
   + column_969 + column_981 + column_982 + column_983 + column_986
   + column_987 + column_989 + column_993 + column_994 + column_995
   + column_998 + column_999 + column_3291 + column_3292 + column_3293
   + column_3295 + column_3296 + column_3298 + column_3301 + column_3302
   + column_3303 + column_3305 + column_3306 + column_3308 >= 1
 each_partition_colored_once_constraint1: column_2 + column_951
   + column_953 + column_967 + column_983 + column_984 + column_986
   + column_987 + column_988 + column_989 + column_995 + column_996
   + column_998 + column_999 + column_3293 + column_3294 + column_3295
   + column_3296 + column_3297 + column_3298 + column_3303 + column_3304
   + column_3305 + column_3306 + column_3307 + column_3308 >= 1
 each_partition_colored_once_constraint2: column_3 + column_950
   + column_951 + column_952 + column_953 + column_956 + column_966
   + column_967 + column_968 + column_969 + column_989 >= 1
 each_partition_colored_once_constraint3: column_4 + column_941
   + column_966 + column_967 + column_968 >= 1
 each_partition_colored_once_constraint4: column_1 + column_950
   + column_951 + column_952 + column_953 + column_956 + column_3290
   + column_3291 + column_3292 + column_3293 + column_3294 + column_3295
   + column_3296 + column_3297 + column_3298 >= 1
 each_partition_colored_once_constraint5: column_2 + column_111
   + column_941 + column_956 >= 1
 each_partition_colored_once_constraint6: column_3 + column_950
   + column_951 + column_952 + column_953 + column_956 + column_3300
   + column_3301 + column_3302 + column_3303 + column_3304 + column_3305
   + column_3306 + column_3307 + column_3308 >= 1
 each_partition_colored_once_constraint7: column_4 + column_81 + column_83
   + column_85 + column_251 + column_253 + column_255 + column_950
   + column_951 + column_952 + column_953 + column_956 >= 1
 each_partition_colored_once_constraint8: column_1 + column_90 + column_91
   + column_93 + column_95 + column_950 + column_951 + column_952
   + column_953 + column_956 + column_966 + column_967 + column_968
   + column_969 >= 1
 each_partition_colored_once_constraint9: column_2 + column_251
   + column_253 + column_255 + column_966 + column_967 + column_968
   + column_969 >= 1
 each_partition_colored_once_constraint10: column_3 + column_941 >= 1
 each_partition_colored_once_constraint11: column_4 + column_941
   + column_950 + column_951 + column_952 + column_953 + column_956
   + column_966 + column_967 + column_968 + column_969 >= 1
 each_partition_colored_once_constraint12: column_1 + column_251
   + column_253 + column_255 + column_941 >= 1
 each_partition_colored_once_constraint13: column_2 + column_980
   + column_981 + column_982 + column_983 + column_984 + column_986
   + column_987 + column_988 + column_989 + column_990 >= 1
 each_partition_colored_once_constraint14: column_3 + column_251
   + column_253 + column_255 + column_941 >= 1
 each_partition_colored_once_constraint15: column_4 + column_251
   + column_253 + column_255 + column_969 >= 1
 each_partition_colored_once_constraint16: column_1 + column_950
   + column_951 + column_952 + column_953 + column_956 + column_966
   + column_967 + column_968 + column_969 >= 1
 each_partition_colored_once_constraint17: column_2 + column_966
   + column_967 + column_968 + column_969 + column_3290 + column_3291
   + column_3292 + column_3293 + column_3294 + column_3295 + column_3296
   + column_3297 + column_3298 + column_3300 + column_3301 + column_3302
   + column_3303 + column_3304 + column_3305 + column_3306 + column_3307
   + column_3308 >= 1
 each_partition_colored_once_constraint18: column_3 + column_61 + column_63
   + column_65 + column_170 + column_172 + column_174 + column_251
   + column_253 + column_255 + column_950 + column_951 + column_952
   + column_953 + column_956 + column_966 + column_967 + column_968
   + column_969 >= 1
 each_partition_colored_once_constraint19: column_4 + column_990
   + column_991 + column_992 + column_993 + column_994 + column_995
   + column_996 + column_998 + column_999 >= 1
 makespan_vertex_0: T - column_1 >= 0
 makespan_vertex_1: T - 9 column_63 - 9 column_83 - 9 column_93
   - 9 column_172 - 9 column_253 - 9 column_966 - 9 column_967
   - 9 column_969 - 9 column_981 - 9 column_983 - 9 column_987
   - 9 column_989 - 9 column_993 - 9 column_995 - 9 column_999
   - 9 column_3291 - 9 column_3293 - 9 column_3296 - 9 column_3301
   - 9 column_3303 - 9 column_3306 >= 0
 makespan_vertex_2: T - 9 column_65 - 9 column_85 - 9 column_95
   - 9 column_174 - 9 column_255 - 9 column_982 - 9 column_986
   - 9 column_994 - 9 column_998 - 9 column_3292 - 9 column_3295
   - 9 column_3298 - 9 column_3302 - 9 column_3305 - 9 column_3308 >= 0
 makespan_vertex_3: T - 2 column_2 >= 0
 makespan_vertex_4: T - 2 column_951 - 2 column_953 - 2 column_967
   - 2 column_983 - 2 column_984 - 2 column_986 - 2 column_995
   - 2 column_996 - 2 column_998 - 2 column_3293 - 2 column_3294
   - 2 column_3295 - 2 column_3303 - 2 column_3304 - 2 column_3305 >= 0
 makespan_vertex_5: T - 3 column_987 - 3 column_988 - 3 column_989
   - 3 column_999 - 3 column_3296 - 3 column_3297 - 3 column_3298
   - 3 column_3306 - 3 column_3307 - 3 column_3308 >= 0
 makespan_vertex_6: T >= 0
 makespan_vertex_7: T - 3 column_3 >= 0
 makespan_vertex_8: T - 5 column_950 - 5 column_951 - 5 column_952
   - 5 column_953 - 5 column_956 - 5 column_966 - 5 column_967
   - 5 column_968 - 5 column_969 - 5 column_989 >= 0
 makespan_vertex_9: T - 4 column_4 >= 0
 makespan_vertex_10: T - 4 column_941 - 4 column_966 - 4 column_967
   - 4 column_968 >= 0
 makespan_vertex_11: T - 5 column_1 >= 0
 makespan_vertex_12: T - 10 column_950 - 10 column_951 - 10 column_952
   - 10 column_953 - 10 column_956 - 10 column_3290 - 10 column_3291
   - 10 column_3292 - 10 column_3293 - 10 column_3294 - 10 column_3295
   - 10 column_3296 - 10 column_3297 - 10 column_3298 >= 0
 makespan_vertex_13: T - 6 column_2 >= 0
 makespan_vertex_14: T - 2 column_111 - 2 column_941 - 2 column_956 >= 0
 makespan_vertex_15: T - 7 column_3 - 7 column_950 - 7 column_951
   - 7 column_952 - 7 column_953 - 7 column_956 - 7 column_3300
   - 7 column_3301 - 7 column_3302 - 7 column_3303 - 7 column_3304
   - 7 column_3305 - 7 column_3306 - 7 column_3307 - 7 column_3308 >= 0
 makespan_vertex_16: T >= 0
 makespan_vertex_17: T - 8 column_4 - 8 column_81 - 8 column_83
   - 8 column_85 - 8 column_251 - 8 column_253 - 8 column_255
   - 8 column_950 - 8 column_951 - 8 column_952 - 8 column_953
   - 8 column_956 >= 0
 makespan_vertex_18: T >= 0
 makespan_vertex_19: T >= 0
 makespan_vertex_20: T >= 0
 makespan_vertex_21: T - 9 column_1 - 9 column_91 - 9 column_950
   - 9 column_951 - 9 column_952 - 9 column_953 - 9 column_956
   - 9 column_968 >= 0
 makespan_vertex_22: T - 10 column_90 - 10 column_93 - 10 column_95
   - 10 column_966 - 10 column_967 - 10 column_969 >= 0
 makespan_vertex_23: T >= 0
 makespan_vertex_24: T - 10 column_2 >= 0
 makespan_vertex_25: T >= 0
 makespan_vertex_26: T >= 0
 makespan_vertex_27: T - 6 column_251 - 6 column_253 - 6 column_255
   - 6 column_966 - 6 column_967 - 6 column_968 - 6 column_969 >= 0
 makespan_vertex_28: T - 11 column_3 >= 0
 makespan_vertex_29: T - 6 column_941 >= 0
 makespan_vertex_30: T - 12 column_4 >= 0
 makespan_vertex_31: T >= 0
 makespan_vertex_32: T - 3 column_941 - 3 column_950 - 3 column_951
   - 3 column_952 - 3 column_953 - 3 column_956 - 3 column_966
   - 3 column_967 - 3 column_968 - 3 column_969 >= 0
 makespan_vertex_33: T - column_1 - column_251 - column_253 - column_255
   - column_941 >= 0
 makespan_vertex_34: T >= 0
 makespan_vertex_35: T - 2 column_2 >= 0
 makespan_vertex_36: T - 10 column_980 - 10 column_981 - 10 column_982
   - 10 column_983 - 10 column_984 - 10 column_986 - 10 column_987
   - 10 column_988 - 10 column_989 - 10 column_990 >= 0
 makespan_vertex_37: T - 3 column_3 - 3 column_251 - 3 column_253
   - 3 column_255 >= 0
 makespan_vertex_38: T - 5 column_941 >= 0
 makespan_vertex_39: T - 4 column_4 - 4 column_969 >= 0
 makespan_vertex_40: T >= 0
 makespan_vertex_41: T - 11 column_251 - 11 column_253 - 11 column_255
   >= 0
 makespan_vertex_42: T - 5 column_1 >= 0
 makespan_vertex_43: T - column_952 - column_953 - column_956 - column_966
   - column_967 - column_968 - column_969 >= 0
 makespan_vertex_44: T - 6 column_950 - 6 column_951 >= 0
 makespan_vertex_45: T - 6 column_2 - 6 column_3290 - 6 column_3291
   - 6 column_3292 - 6 column_3293 - 6 column_3294 - 6 column_3295
   - 6 column_3296 - 6 column_3297 - 6 column_3298 - 6 column_3300
   - 6 column_3301 - 6 column_3302 - 6 column_3303 - 6 column_3304
   - 6 column_3305 - 6 column_3306 - 6 column_3307 - 6 column_3308 >= 0
 makespan_vertex_46: T >= 0
 makespan_vertex_47: T - 8 column_966 - 8 column_967 - 8 column_968
   - 8 column_969 >= 0
 makespan_vertex_48: T - 7 column_3 - 7 column_61 - 7 column_63
   - 7 column_65 - 7 column_966 - 7 column_967 - 7 column_968
   - 7 column_969 >= 0
 makespan_vertex_49: T - 4 column_170 - 4 column_172 - 4 column_174
   - 4 column_251 - 4 column_253 - 4 column_255 - 4 column_950
   - 4 column_951 - 4 column_952 - 4 column_953 - 4 column_956 >= 0
 makespan_vertex_50: T >= 0
 makespan_vertex_51: T - 8 column_4 - 8 column_990 - 8 column_992
   - 8 column_993 - 8 column_994 - 8 column_995 - 8 column_996
   - 8 column_998 - 8 column_999 >= 0
 makespan_vertex_52: T - 5 column_991 >= 0
 charger_capacity_constraint: column_1 + column_2 + column_3 + column_4
   + column_61 + column_63 + column_65 + column_81 + column_83 + column_85
   + column_90 + column_91 + column_93 + column_95 + column_111
   + column_170 + column_172 + column_174 + column_251 + column_253
   + column_255 + column_941 + column_950 + column_951 + column_952
   + column_953 + column_956 + column_966 + column_967 + column_968
   + column_969 + column_980 + column_981 + column_982 + column_983
   + column_984 + column_986 + column_987 + column_988 + column_989
   + column_990 + column_991 + column_992 + column_993 + column_994
   + column_995 + column_996 + column_998 + column_999 + column_3290
   + column_3291 + column_3292 + column_3293 + column_3294 + column_3295
   + column_3296 + column_3297 + column_3298 + column_3300 + column_3301
   + column_3302 + column_3303 + column_3304 + column_3305 + column_3306
   + column_3307 + column_3308 <= 4
Bounds
End
