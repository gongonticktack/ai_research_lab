import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
let scene,camera,renderer,controls,object;
export async function init(container){
  scene=new THREE.Scene();scene.background=new THREE.Color('#10171d');
  camera=new THREE.PerspectiveCamera(45,1,.01,10000);
  renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));container.append(renderer.domElement);
  controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;
  scene.add(new THREE.HemisphereLight(0xffffff,0x334455,3));
  const light=new THREE.DirectionalLight(0xffffff,3);light.position.set(3,4,5);scene.add(light);
  new ResizeObserver(()=>{const w=container.clientWidth,h=container.clientHeight;renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();}).observe(container);
  reset();renderer.setAnimationLoop(()=>{controls.update();renderer.render(scene,camera);});
}
export function reset(){camera.position.set(2,1.4,3);controls.target.set(0,0,0);controls.update();}
export function show(mesh){
  if(!Array.isArray(mesh.vertices)||!Array.isArray(mesh.faces))throw Error('Invalid mesh');
  if(mesh.vertices.length>200000||mesh.faces.length>400000)throw Error('Mesh too large');
  if(mesh.vertices.some(v=>v.length!==3||v.some(x=>!Number.isFinite(x)))||mesh.faces.some(f=>f.length!==3||f.some(i=>!Number.isInteger(i)||i<0||i>=mesh.vertices.length)))throw Error('Invalid geometry');
  if(object){scene.remove(object);object.geometry.dispose();object.material.dispose();}
  const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(mesh.vertices.flat(),3));geometry.setIndex(mesh.faces.flat());geometry.computeVertexNormals();geometry.center();geometry.computeBoundingSphere();
  object=new THREE.Mesh(geometry,new THREE.MeshStandardMaterial({color:0x80cdb5,roughness:.45,side:THREE.DoubleSide}));
  // SAM outputs camera coordinates (+Y down). Three.js uses +Y up.
  if(mesh.coordinate_system==='opencv-camera')object.rotation.x=Math.PI;
  const radius=geometry.boundingSphere.radius;if(radius>0)object.scale.setScalar(1/radius);scene.add(object);reset();
}
