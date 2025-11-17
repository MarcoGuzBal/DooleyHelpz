export function getOrCreateSharedId(): number {
  let id = localStorage.getItem("anon_shared_id");
  if (!id) {
    id = String(Math.floor(Math.random() * 900000) + 100000); 
    localStorage.setItem("anon_shared_id", id);
  }
  return Number(id);
}
