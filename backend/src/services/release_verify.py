from fractions import Fraction
def _rref(matrix,width):
 """独立的高斯-若尔当精确消元：返回(变换后矩阵,主元列列表)。"""
 rows=[list(r) for r in matrix];rank=0;pivots=[]
 for col in range(width):
  pivot=next((i for i in range(rank,len(rows)) if rows[i][col]),None)
  if pivot is None: continue
  rows[rank],rows[pivot]=rows[pivot],rows[rank]
  inv=Fraction(1)/rows[rank][col]
  rows[rank]=[v*inv for v in rows[rank]]
  for i in range(len(rows)):
   if i!=rank and rows[i][col]:
    factor=rows[i][col]
    rows[i]=[a-factor*b for a,b in zip(rows[i],rows[rank])]
  pivots.append(col);rank+=1
 return rows,pivots
def solve(matrix,rhs):
 """精确求解 matrix·x = rhs，返回一个特解；无解返回 None。"""
 if not matrix: return None if any(rhs) else []
 width=len(matrix[0])
 rows,pivots=_rref([list(row)+[Fraction(rhs[i])] for i,row in enumerate(matrix)],width)
 for i,row in enumerate(rows):
  if i>=len(pivots) and row[width]: return None
 answer=[Fraction(0)]*width
 for i,col in enumerate(pivots): answer[col]=rows[i][width]
 return answer
def verify(departments,confidential,equations):
 """独立精确消元验证跨次泄密：与准入裁决不同的实现路径，用于复核。
 对每条方程建立稠密矩阵，逐一求解 A^T·y = e_j 判断保密部门是否被唯一解出。"""
 index={name:i for i,name in enumerate(departments)}
 matrix=[[Fraction(0)]*len(departments) for _ in equations]
 for i,eq in enumerate(equations):
  for dept,coef in eq['coefficients'].items():
   if dept in index: matrix[i][index[dept]]=coef
 transposed=[[matrix[r][c] for r in range(len(matrix))] for c in range(len(departments))]
 leaks=[]
 for dept in confidential:
  col=index.get(dept)
  if col is None: continue
  unit=[Fraction(1) if i==col else Fraction(0) for i in range(len(departments))]
  combo=solve(transposed,unit)
  if combo is None: continue
  value=sum((a*eq['value'] for a,eq in zip(combo,equations)),Fraction(0))
  steps=[{'label':eq['label'],'coefficient':str(a)} for a,eq in zip(combo,equations) if a]
  leaks.append({'department':dept,'value':str(value),'combination':steps})
 _,pivots=_rref(matrix,len(departments))
 return {'rank':len(pivots),'leaks':leaks}
