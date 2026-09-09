export interface CityBuilding { id: string; ring: [number, number][]; h: number; core: boolean; change?: { type: string; year: number; from: number } }
export interface CityData { origin: [number, number]; buildings: CityBuilding[]; core: [number, number][][]; buffer: [number, number][][]; years: [number, number]; attribution: string }
