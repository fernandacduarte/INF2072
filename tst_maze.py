from custom_environment.utils import build_maze, is_connected                                                       
from custom_environment.env.domain.constant import Observation                                                      
g = build_maze('pinklike')                                                                                          
print('shape', g.shape)                                                                                             
print('connected', is_connected(g))                                                                                 
border_ok = (g[0,:]==Observation.WALL.value).all() and (g[-1,:]==Observation.WALL.value).all() and (g[:,0]==Observation.WALL.value).all() and (g[:,-1]==Observation.WALL.value).all()                                  
print('border_ok', bool(border_ok))                                                                                 
spawns = [(1,1),(1,18),(18,9)]                                                                                      
print('spawns_open', all(g[r,c]==Observation.EMPTY.value for r,c in spawns))                                        
print('default_shape', build_maze('default').shape)
