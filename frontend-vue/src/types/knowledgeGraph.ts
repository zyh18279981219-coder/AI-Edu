export interface KnowledgeGraphResponse {
    name?: string;
    flag?: string;
    children?: CourseNode[];
}

export interface CourseNode {
    id?: number;
    name: string;
    flag?: string;
    description?: string;
    resource_path?: string[] | string;
    grandchildren?: CourseNode[];
    "great-grandchildren"?: CourseNode[];
}

export type CurrentNodeInfo = {
  name: string;
  index: number;
  total: number;
  completed: number;
};