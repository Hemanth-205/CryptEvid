import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  Network,
  Search,
  RefreshCw,
  ZoomIn,
  ZoomOut,
  Maximize2,
  FolderLock,
  ExternalLink,
  Database,
  ChevronRight,
  Copy,
  Check,
  FileText
} from 'lucide-react';
import { caseApi, analyticsApi } from '../services/api';
import type { Case, EvidenceGraphResponse, GraphNode } from '../types';

interface SimulationNode {
  id: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  w: number;
  h: number;
  r: number;
  pinned: boolean;
  node: GraphNode;
  color: string;
  borderColor: string;
  bgColor: string;
  textColor: string;
  categoryLabel: string;
}

type LayoutMode = 'TREE' | 'LAYERED' | 'FORCE';

export const EvidenceGraphPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialCaseId = searchParams.get('caseId') || localStorage.getItem('cryptevid_active_case_id') || '';

  const [cases, setCases] = useState<Case[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>(initialCaseId);
  const [, setLoadingCases] = useState<boolean>(true);
  const [seeding, setSeeding] = useState<boolean>(false);

  // Graph state
  const [graphData, setGraphData] = useState<EvidenceGraphResponse | null>(null);
  const [graphLoading, setGraphLoading] = useState<boolean>(false);
  const [graphFilterType, setGraphFilterType] = useState<string>('ALL');
  const [graphSearch, setGraphSearch] = useState<string>('');
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const [layoutMode, setLayoutMode] = useState<LayoutMode>('TREE');
  const [showCustodyNodes, setShowCustodyNodes] = useState<boolean>(true);
  const [copiedHash, setCopiedHash] = useState<boolean>(false);

  // Canvas pan & zoom
  const [graphZoom, setGraphZoom] = useState<number>(1);
  const [graphPan, setGraphPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState<boolean>(false);
  const [panStart, setPanStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // Node dragging state
  const [draggedNodeId, setDraggedNodeId] = useState<string | null>(null);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const simulationNodesRef = useRef<Map<string, SimulationNode>>(new Map());
  const animFrameRef = useRef<number | null>(null);

  // Load Cases
  const loadCases = async () => {
    setLoadingCases(true);
    try {
      const res = await caseApi.getCases({ limit: 100 });
      const caseList: Case[] = res.cases || [];
      setCases(caseList);

      if (caseList.length > 0) {
        // If initial case ID matches an existing case, use it; otherwise default to first case
        const matched = caseList.find((c: Case) => c._id === selectedCaseId);
        if (!matched) {
          const firstId = caseList[0]._id;
          setSelectedCaseId(firstId);
          localStorage.setItem('cryptevid_active_case_id', firstId);
        }
      }
    } catch (err) {
      console.error('Failed to load cases', err);
    } finally {
      setLoadingCases(false);
    }
  };

  useEffect(() => {
    loadCases();
  }, []);

  const handleCaseChange = (newCaseId: string) => {
    setSelectedCaseId(newCaseId);
    localStorage.setItem('cryptevid_active_case_id', newCaseId);
    setSearchParams({ caseId: newCaseId });
  };

  // Handle Demo Seed
  const handleSeedDemo = async () => {
    setSeeding(true);
    try {
      await caseApi.seedDemo();
      await loadCases();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to seed demo case.');
    } finally {
      setSeeding(false);
    }
  };

  // Load Graph for Selected Case
  const loadGraph = useCallback(async () => {
    if (!selectedCaseId) return;
    setGraphLoading(true);
    try {
      const params: any = {};
      if (graphFilterType !== 'ALL') params.node_type = graphFilterType;
      const data = await analyticsApi.getCaseGraph(selectedCaseId, params);
      setGraphData(data);
    } catch (err) {
      console.error('Failed to load evidence graph', err);
    } finally {
      setGraphLoading(false);
    }
  }, [selectedCaseId, graphFilterType]);

  useEffect(() => {
    if (selectedCaseId) {
      loadGraph();
      setSelectedNode(null);
    }
  }, [selectedCaseId, loadGraph]);

  const activeCase = cases.find(c => c._id === selectedCaseId);

  // Classify Entity Type Visuals (Crisp, High-Contrast Professional Light Theme)
  const getNodeVisuals = (node: GraphNode) => {
    const nt = String(node.node_type || '').toUpperCase();
    const integrity = node.metadata?.integrity_status;
    const isTampered = integrity === 'TAMPERED';
    const sev = node.metadata?.severity || node.severity || 'INFO';

    if (nt === 'CASE') {
      return {
        color: '#0F172A',
        borderColor: '#2563EB',
        bgColor: '#EFF6FF',
        textColor: '#1D4ED8',
        categoryLabel: 'CASE ROOT',
        w: 170,
        h: 46,
        r: 28
      };
    }
    if (nt === 'EVIDENCE' || nt === 'FILE') {
      if (isTampered) {
        return {
          color: '#7F1D1D',
          borderColor: '#EF4444',
          bgColor: '#FEF2F2',
          textColor: '#DC2626',
          categoryLabel: 'EVIDENCE (TAMPERED)',
          w: 160,
          h: 42,
          r: 22
        };
      }
      return {
        color: '#0F172A',
        borderColor: '#0284C7',
        bgColor: '#F0F9FF',
        textColor: '#0369A1',
        categoryLabel: 'EVIDENCE FILE',
        w: 160,
        h: 42,
        r: 22
      };
    }
    if (nt === 'BACKUP') {
      return {
        color: '#78350F',
        borderColor: '#D97706',
        bgColor: '#FFFBEB',
        textColor: '#B45309',
        categoryLabel: 'VAULT BACKUP',
        w: 150,
        h: 40,
        r: 20
      };
    }
    if (nt === 'EVENT') {
      const isCrit = sev === 'CRITICAL' || sev === 'HIGH';
      return {
        color: isCrit ? '#7F1D1D' : '#0F172A',
        borderColor: isCrit ? '#EF4444' : '#64748B',
        bgColor: isCrit ? '#FEF2F2' : '#F8FAFC',
        textColor: isCrit ? '#DC2626' : '#475569',
        categoryLabel: `EVENT [${sev}]`,
        w: 155,
        h: 40,
        r: 20
      };
    }
    if (nt === 'DEVICE') {
      return {
        color: '#0F172A',
        borderColor: '#3B82F6',
        bgColor: '#EFF6FF',
        textColor: '#1D4ED8',
        categoryLabel: 'HARDWARE TERMINAL',
        w: 150,
        h: 40,
        r: 20
      };
    }
    if (nt === 'INVESTIGATOR' || nt === 'PERSON') {
      return {
        color: '#064E3B',
        borderColor: '#16A34A',
        bgColor: '#F0FDF4',
        textColor: '#15803D',
        categoryLabel: 'INVESTIGATOR',
        w: 150,
        h: 40,
        r: 20
      };
    }
    if (nt === 'LOCATION') {
      return {
        color: '#581C87',
        borderColor: '#9333EA',
        bgColor: '#FAF5FF',
        textColor: '#7E22CE',
        categoryLabel: 'SCENE LOCATION',
        w: 140,
        h: 38,
        r: 18
      };
    }
    if (nt === 'CUSTODY') {
      return {
        color: '#0F172A',
        borderColor: '#64748B',
        bgColor: '#F8FAFC',
        textColor: '#334155',
        categoryLabel: 'CUSTODY BLOCK',
        w: 140,
        h: 38,
        r: 18
      };
    }
    if (nt === 'THREAT_ACTOR' || nt === 'IP_ADDRESS' || nt === 'ACTOR') {
      return {
        color: '#7F1D1D',
        borderColor: '#DC2626',
        bgColor: '#FEF2F2',
        textColor: '#B91C1C',
        categoryLabel: 'THREAT ACTOR',
        w: 150,
        h: 40,
        r: 22
      };
    }
    return {
      color: '#0F172A',
      borderColor: '#CBD5E1',
      bgColor: '#F8FAFC',
      textColor: '#64748B',
      categoryLabel: 'ENTITY',
      w: 140,
      h: 38,
      r: 18
    };
  };

  // Auto-fit graph nodes comfortably in the canvas viewport
  const fitToView = useCallback(() => {
    const nodes = Array.from(simulationNodesRef.current.values());
    if (nodes.length === 0) {
      setGraphZoom(1);
      setGraphPan({ x: 0, y: 0 });
      return;
    }
    const canvas = canvasRef.current;
    const w = canvas ? canvas.clientWidth : 800;
    const h = canvas ? canvas.clientHeight : 650;

    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    nodes.forEach(n => {
      const hw = (n.w || 150) / 2;
      const hh = (n.h || 40) / 2;
      if (n.x - hw < minX) minX = n.x - hw;
      if (n.x + hw > maxX) maxX = n.x + hw;
      if (n.y - hh < minY) minY = n.y - hh;
      if (n.y + hh > maxY) maxY = n.y + hh;
    });

    const graphW = Math.max(100, maxX - minX + 160);
    const graphH = Math.max(100, maxY - minY + 160);
    const midX = (minX + maxX) / 2;
    const midY = (minY + maxY) / 2;

    const scaleX = w / graphW;
    const scaleY = h / graphH;
    const newZoom = Math.min(1.1, Math.max(0.45, Math.min(scaleX, scaleY) * 0.92));

    setGraphZoom(newZoom);
    setGraphPan({
      x: -midX * newZoom,
      y: -midY * newZoom
    });
  }, []);

  // Structured Deterministic Graph Layout Calculation (Clean Multi-Row Hierarchical Grid with Collision Separation)
  useEffect(() => {
    if (!graphData || !graphData.nodes) return;

    const newMap = new Map<string, SimulationNode>();
    const rawNodes = graphData.nodes;

    // Filter nodes based on custody visibility
    const nodes = rawNodes.filter(n => {
      if (!showCustodyNodes && String(n.node_type).toUpperCase() === 'CUSTODY') {
        return false;
      }
      return true;
    });

    // Group nodes by structured architectural tiers
    const caseNodes = nodes.filter(n => String(n.node_type).toUpperCase() === 'CASE');
    const deviceNodes = nodes.filter(n => ['DEVICE', 'INVESTIGATOR', 'LOCATION'].includes(String(n.node_type).toUpperCase()));
    const evidenceNodes = nodes.filter(n => ['EVIDENCE', 'FILE', 'BACKUP'].includes(String(n.node_type).toUpperCase()));
    const custodyNodes = nodes.filter(n => String(n.node_type).toUpperCase() === 'CUSTODY');
    const threatAndAlertNodes = nodes.filter(n => ['EVENT', 'SECURITY_ALERT', 'THREAT_ACTOR', 'IP_ADDRESS', 'ACTOR'].includes(String(n.node_type).toUpperCase()));

    nodes.forEach(n => {
      const v = getNodeVisuals(n);
      let targetX = 0;
      let targetY = 0;

      if (layoutMode === 'TREE') {
        // Deterministic Top-Down Forensic Hierarchy
        if (caseNodes.some(cn => cn.id === n.id)) {
          const idx = caseNodes.findIndex(cn => cn.id === n.id);
          targetX = (idx - (caseNodes.length - 1) / 2) * 280;
          targetY = -270;
        } else if (deviceNodes.some(dn => dn.id === n.id)) {
          const idx = deviceNodes.findIndex(dn => dn.id === n.id);
          const cols = Math.min(4, Math.max(1, deviceNodes.length));
          const col = idx % cols;
          const row = Math.floor(idx / cols);
          targetX = (col - (cols - 1) / 2) * 230;
          targetY = -130 + row * 75;
        } else if (evidenceNodes.some(en => en.id === n.id)) {
          const idx = evidenceNodes.findIndex(en => en.id === n.id);
          const cols = Math.min(3, Math.max(1, evidenceNodes.length));
          const col = idx % cols;
          const row = Math.floor(idx / cols);
          targetX = (col - (cols - 1) / 2) * 260;
          targetY = 40 + row * 80;
        } else if (custodyNodes.some(cn => cn.id === n.id)) {
          const idx = custodyNodes.findIndex(cn => cn.id === n.id);
          const cols = Math.min(4, Math.max(1, custodyNodes.length));
          const col = idx % cols;
          const row = Math.floor(idx / cols);
          targetX = (col - (cols - 1) / 2) * 210;
          targetY = 200 + row * 70;
        } else {
          const idx = threatAndAlertNodes.findIndex(tn => tn.id === n.id);
          const cols = Math.min(3, Math.max(1, threatAndAlertNodes.length));
          const col = idx % cols;
          const row = Math.floor(idx / cols);
          const baseOffset = 200 + (custodyNodes.length > 0 ? Math.ceil(custodyNodes.length / 4) * 70 + 40 : 0);
          targetX = (col - (cols - 1) / 2) * 240;
          targetY = baseOffset + row * 75;
        }
      } else if (layoutMode === 'LAYERED') {
        // Horizontal Left-to-Right Investigation Pipeline
        if (caseNodes.some(cn => cn.id === n.id)) {
          targetX = -460;
          targetY = 0;
        } else if (deviceNodes.some(dn => dn.id === n.id)) {
          const idx = deviceNodes.findIndex(dn => dn.id === n.id);
          targetX = -230;
          targetY = (idx - (deviceNodes.length - 1) / 2) * 85;
        } else if (evidenceNodes.some(en => en.id === n.id)) {
          const idx = evidenceNodes.findIndex(en => en.id === n.id);
          targetX = 30;
          targetY = (idx - (evidenceNodes.length - 1) / 2) * 90;
        } else if (custodyNodes.some(cn => cn.id === n.id)) {
          const idx = custodyNodes.findIndex(cn => cn.id === n.id);
          const row = idx % 5;
          const col = Math.floor(idx / 5);
          targetX = 270 + col * 170;
          targetY = (row - 2) * 70;
        } else {
          const idx = threatAndAlertNodes.findIndex(tn => tn.id === n.id);
          targetX = 520;
          targetY = (idx - (threatAndAlertNodes.length - 1) / 2) * 80;
        }
      } else {
        // Concentric Orbital Layout
        const idx = nodes.findIndex(node => node.id === n.id);
        if (String(n.node_type).toUpperCase() === 'CASE') {
          targetX = 0;
          targetY = 0;
        } else if (deviceNodes.some(dn => dn.id === n.id)) {
          const didx = deviceNodes.findIndex(dn => dn.id === n.id);
          const count = deviceNodes.length || 1;
          const angle = (didx / count) * 2 * Math.PI - Math.PI / 2;
          targetX = Math.cos(angle) * 190;
          targetY = Math.sin(angle) * 190;
        } else if (evidenceNodes.some(en => en.id === n.id)) {
          const eidx = evidenceNodes.findIndex(en => en.id === n.id);
          const count = evidenceNodes.length || 1;
          const angle = (eidx / count) * 2 * Math.PI - Math.PI / 4;
          targetX = Math.cos(angle) * 330;
          targetY = Math.sin(angle) * 330;
        } else {
          const count = Math.max(1, custodyNodes.length + threatAndAlertNodes.length);
          const angle = (idx / count) * 2 * Math.PI;
          targetX = Math.cos(angle) * 470;
          targetY = Math.sin(angle) * 470;
        }
      }

      newMap.set(n.id, {
        id: n.id,
        x: targetX,
        y: targetY,
        vx: 0,
        vy: 0,
        w: v.w,
        h: v.h,
        r: v.r,
        pinned: String(n.node_type) === 'CASE',
        node: n,
        color: v.color,
        borderColor: v.borderColor,
        bgColor: v.bgColor,
        textColor: v.textColor,
        categoryLabel: v.categoryLabel
      });
    });

    // Run Iterative Anti-Collision Relaxation to mathematically guarantee NO overlapping cards
    const simList = Array.from(newMap.values());
    for (let iter = 0; iter < 35; iter++) {
      for (let i = 0; i < simList.length; i++) {
        for (let j = i + 1; j < simList.length; j++) {
          const a = simList[i];
          const b = simList[j];
          const minW = (a.w + b.w) / 2 + 25;
          const minH = (a.h + b.h) / 2 + 20;
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          if (Math.abs(dx) < minW && Math.abs(dy) < minH) {
            const overlapX = minW - Math.abs(dx);
            const overlapY = minH - Math.abs(dy);
            if (overlapX < overlapY) {
              const push = (overlapX / 2) * (dx <= 0 ? -1 : 1);
              if (!a.pinned) a.x -= push;
              if (!b.pinned) b.x += push;
            } else {
              const push = (overlapY / 2) * (dy <= 0 ? -1 : 1);
              if (!a.pinned) a.y -= push;
              if (!b.pinned) b.y += push;
            }
          }
        }
      }
    }

    simulationNodesRef.current = newMap;
    // Auto-center view on initial load or layout switch
    setTimeout(fitToView, 60);
  }, [graphData, layoutMode, showCustodyNodes, fitToView]);

  // Main Canvas Render Loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let isRunning = true;

    const render = () => {
      if (!isRunning) return;

      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      if (canvas.width !== Math.floor(rect.width * dpr) || canvas.height !== Math.floor(rect.height * dpr)) {
        canvas.width = Math.floor(rect.width * dpr);
        canvas.height = Math.floor(rect.height * dpr);
      }
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.scale(dpr, dpr);

      const w = rect.width;
      const h = rect.height;

      // Pure Crisp White Workstation Canvas
      ctx.fillStyle = '#FFFFFF';
      ctx.fillRect(0, 0, w, h);

      // Clean Precision Dot Grid (Light Theme)
      ctx.fillStyle = '#E2E8F0';
      const gridSize = 24 * graphZoom;
      const offsetX = (w / 2 + graphPan.x) % gridSize;
      const offsetY = (h / 2 + graphPan.y) % gridSize;

      for (let x = offsetX; x < w; x += gridSize) {
        for (let y = offsetY; y < h; y += gridSize) {
          ctx.fillRect(x - 0.75, y - 0.75, 1.5, 1.5);
        }
      }

      const simMap = simulationNodesRef.current;
      const simNodes = Array.from(simMap.values());
      const edges = graphData?.edges || [];

      // Apply Canvas Pan & Zoom
      ctx.save();
      ctx.translate(w / 2 + graphPan.x, h / 2 + graphPan.y);
      ctx.scale(graphZoom, graphZoom);

      const searchLower = graphSearch.toLowerCase().trim();
      const isSearchActive = searchLower.length > 0;

      // Find highlighted connection IDs
      const activeNodeId = selectedNode?.id || hoveredNode?.id;
      const directConnectedNodeIds = new Set<string>();
      if (activeNodeId) {
        directConnectedNodeIds.add(activeNodeId);
        edges.forEach(e => {
          if (e.source === activeNodeId) directConnectedNodeIds.add(e.target);
          if (e.target === activeNodeId) directConnectedNodeIds.add(e.source);
        });
      }

      // Draw Edges (Clean Smooth Connectors)
      edges.forEach(edge => {
        const s = simMap.get(edge.source);
        const t = simMap.get(edge.target);
        if (!s || !t) return;

        const isConnectedToActive = activeNodeId && (edge.source === activeNodeId || edge.target === activeNodeId);
        const isDeemphasized = activeNodeId && !isConnectedToActive;

        let strokeColor = '#CBD5E1';
        let lineWidth = 1.3;

        if (edge.edge_type === 'TAMPER_DETECTED' || edge.label === 'TAMPER_DETECTED') {
          strokeColor = '#EF4444';
          lineWidth = 2.2;
        } else if (isConnectedToActive) {
          strokeColor = '#2563EB';
          lineWidth = 2.4;
        }

        ctx.save();
        ctx.globalAlpha = isDeemphasized ? 0.15 : 1;

        // Draw Smooth Curved Bezier Connectors
        ctx.beginPath();
        ctx.moveTo(s.x, s.y);

        if (layoutMode === 'TREE') {
          const midY = s.y + (t.y - s.y) * 0.5;
          ctx.bezierCurveTo(s.x, midY, t.x, midY, t.x, t.y);
        } else if (layoutMode === 'LAYERED') {
          const midX = s.x + (t.x - s.x) * 0.5;
          ctx.bezierCurveTo(midX, s.y, midX, t.y, t.x, t.y);
        } else {
          ctx.lineTo(t.x, t.y);
        }

        ctx.strokeStyle = strokeColor;
        ctx.lineWidth = lineWidth;
        ctx.stroke();

        // Directional Arrow Marker
        const angle = Math.atan2(t.y - s.y, t.x - s.x);
        const targetRadius = (t.w ? t.w / 2 : 25) + 3;
        const arrowDist = Math.hypot(t.x - s.x, t.y - s.y) - targetRadius;
        const arrowX = s.x + Math.cos(angle) * Math.max(arrowDist, 10);
        const arrowY = s.y + Math.sin(angle) * Math.max(arrowDist, 10);

        ctx.save();
        ctx.translate(arrowX, arrowY);
        ctx.rotate(angle);
        ctx.fillStyle = isConnectedToActive ? '#2563EB' : strokeColor;
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.lineTo(-7, -3.5);
        ctx.lineTo(-7, 3.5);
        ctx.closePath();
        ctx.fill();
        ctx.restore();

        // Edge Relationship Label (ONLY shown on active / hovered selection to eliminate clutter!)
        if (isConnectedToActive) {
          const midX = (s.x + t.x) / 2;
          const midY = (s.y + t.y) / 2;

          ctx.save();
          ctx.font = 'bold 9.5px var(--font-mono, monospace)';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';

          const labelText = edge.label || edge.edge_type;
          const textWidth = ctx.measureText(labelText).width;

          // Box Background
          ctx.fillStyle = '#FFFFFF';
          ctx.fillRect(midX - textWidth / 2 - 5, midY - 8, textWidth + 10, 16);
          ctx.strokeStyle = '#2563EB';
          ctx.lineWidth = 1.2;
          ctx.strokeRect(midX - textWidth / 2 - 5, midY - 8, textWidth + 10, 16);

          ctx.fillStyle = '#1D4ED8';
          ctx.fillText(labelText, midX, midY);
          ctx.restore();
        }

        ctx.restore();
      });

      // Draw Nodes (Structured Forensic Rectangular Badges)
      simNodes.forEach(simNode => {
        const node = simNode.node;
        const isSelected = selectedNode?.id === node.id;
        const isHovered = hoveredNode?.id === node.id;
        const isConnected = directConnectedNodeIds.has(node.id);
        const isDeemphasized = activeNodeId && !isConnected;

        const isMatch = !isSearchActive ||
          node.label.toLowerCase().includes(searchLower) ||
          String(node.node_type || '').toLowerCase().includes(searchLower) ||
          String(node.metadata?.sha256_hash || '').toLowerCase().includes(searchLower);

        ctx.save();
        ctx.globalAlpha = isDeemphasized || !isMatch ? 0.25 : 1;

        const nodeW = simNode.w || 150;
        const nodeH = simNode.h || 40;
        const nodeX = simNode.x - nodeW / 2;
        const nodeY = simNode.y - nodeH / 2;

        // Base Box
        ctx.fillStyle = isSelected ? '#DBEAFE' : isHovered ? '#F1F5F9' : simNode.bgColor;
        ctx.beginPath();
        ctx.roundRect(nodeX, nodeY, nodeW, nodeH, 6);
        ctx.fill();

        // Border
        ctx.lineWidth = isSelected ? 2.5 : isHovered ? 2 : 1.2;
        ctx.strokeStyle = isSelected ? '#2563EB' : isHovered ? '#3B82F6' : simNode.borderColor;
        ctx.stroke();

        // Left Tag Indicator Strip
        ctx.fillStyle = simNode.borderColor;
        ctx.fillRect(nodeX, nodeY + 3, 3.5, nodeH - 6);

        // Category Tag Header (Small Mono)
        ctx.font = 'bold 8.5px var(--font-mono, monospace)';
        ctx.fillStyle = simNode.textColor;
        ctx.textAlign = 'left';
        ctx.textBaseline = 'top';
        ctx.fillText(simNode.categoryLabel, nodeX + 9, nodeY + 5);

        // Main Node Label
        ctx.font = isSelected ? 'bold 11px sans-serif' : '500 11px sans-serif';
        ctx.fillStyle = isSelected ? '#0F172A' : '#1E293B';
        const rawLabel = node.label || 'Entity';
        const displayLabel = rawLabel.length > 20 ? rawLabel.slice(0, 18) + '…' : rawLabel;
        ctx.fillText(displayLabel, nodeX + 9, nodeY + 18);

        // Hash preview or small sub-identifier if file
        if (node.metadata?.sha256_hash) {
          ctx.font = '8px var(--font-mono, monospace)';
          ctx.fillStyle = '#64748B';
          const hashShort = String(node.metadata.sha256_hash).substring(0, 12) + '…';
          ctx.fillText(`SHA: ${hashShort}`, nodeX + 9, nodeY + 30);
        }

        // Integrity Badge Icon (Green check / Red alert)
        if (node.metadata?.integrity_status) {
          const isVerified = node.metadata.integrity_status === 'VERIFIED';
          ctx.fillStyle = isVerified ? '#16A34A' : '#DC2626';
          ctx.beginPath();
          ctx.arc(nodeX + nodeW - 10, nodeY + 12, 3.5, 0, 2 * Math.PI);
          ctx.fill();
        }

        ctx.restore();
      });

      ctx.restore();

      animFrameRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      isRunning = false;
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [graphData, graphZoom, graphPan, graphSearch, selectedNode, hoveredNode, layoutMode]);

  // Coordinate Conversion (Screen to World Space)
  const screenToWorld = useCallback((screenX: number, screenY: number) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    const w = rect.width;
    const h = rect.height;
    const x = (screenX - rect.left - (w / 2 + graphPan.x)) / graphZoom;
    const y = (screenY - rect.top - (h / 2 + graphPan.y)) / graphZoom;
    return { x, y };
  }, [graphPan, graphZoom]);

  // Mouse Interaction Handlers
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const worldPos = screenToWorld(e.clientX, e.clientY);
    const simNodes = Array.from(simulationNodesRef.current.values());

    // Check hit on node box
    let hitNode: SimulationNode | null = null;
    for (let i = simNodes.length - 1; i >= 0; i--) {
      const n = simNodes[i];
      const hw = (n.w || 150) / 2;
      const hh = (n.h || 40) / 2;
      if (
        worldPos.x >= n.x - hw &&
        worldPos.x <= n.x + hw &&
        worldPos.y >= n.y - hh &&
        worldPos.y <= n.y + hh
      ) {
        hitNode = n;
        break;
      }
    }

    if (hitNode) {
      setDraggedNodeId(hitNode.id);
      setSelectedNode(hitNode.node);
    } else {
      setIsPanning(true);
      setPanStart({ x: e.clientX - graphPan.x, y: e.clientY - graphPan.y });
    }
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const worldPos = screenToWorld(e.clientX, e.clientY);

    if (draggedNodeId) {
      const simNode = simulationNodesRef.current.get(draggedNodeId);
      if (simNode) {
        simNode.x = worldPos.x;
        simNode.y = worldPos.y;
        simNode.vx = 0;
        simNode.vy = 0;
      }
    } else if (isPanning) {
      setGraphPan({ x: e.clientX - panStart.x, y: e.clientY - panStart.y });
    } else {
      // Hover detection
      const simNodes = Array.from(simulationNodesRef.current.values());
      let hit: GraphNode | null = null;
      for (let i = simNodes.length - 1; i >= 0; i--) {
        const n = simNodes[i];
        const hw = (n.w || 150) / 2;
        const hh = (n.h || 40) / 2;
        if (
          worldPos.x >= n.x - hw &&
          worldPos.x <= n.x + hw &&
          worldPos.y >= n.y - hh &&
          worldPos.y <= n.y + hh
        ) {
          hit = n.node;
          break;
        }
      }
      setHoveredNode(hit);
    }
  };

  const handleMouseUp = () => {
    setDraggedNodeId(null);
    setIsPanning(false);
  };

  // Mouse Wheel Zoom
  const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
    setGraphZoom(z => Math.min(2.5, Math.max(0.3, Number((z * zoomFactor).toFixed(2)))));
  };

  // Get Connected Nodes and Edges for Selected Entity
  const getConnectedDetails = (node: GraphNode) => {
    if (!graphData) return { incoming: [], outgoing: [] };
    const outgoing = (graphData.edges || [])
      .filter(e => e.source === node.id)
      .map(e => {
        const targetNode = (graphData.nodes || []).find(n => n.id === e.target);
        return { edge: e, targetNode };
      });
    const incoming = (graphData.edges || [])
      .filter(e => e.target === node.id)
      .map(e => {
        const sourceNode = (graphData.nodes || []).find(n => n.id === e.source);
        return { edge: e, sourceNode };
      });
    return { incoming, outgoing };
  };

  const selectedConnections = selectedNode ? getConnectedDetails(selectedNode) : { incoming: [], outgoing: [] };

  const handleCopyHash = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  return (
    <div className="space-y-4 animate-fade-in-up">
      {/* 1. CASE HEADER BAR */}
      <div className="ws-panel p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white border border-slate-200 shadow-xs">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-center shrink-0">
            <FolderLock className="w-4 h-4 text-amber-600" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold text-amber-700">
                {activeCase?.case_number || 'CASE REGISTRY'}
              </span>
              <span className="text-slate-300">|</span>
              <span className="font-semibold text-xs text-slate-900">
                {activeCase?.title || 'Digital Forensics Investigation'}
              </span>
              <span className="ws-badge ws-badge-amber">ACTIVE INVESTIGATION</span>
            </div>
            <div className="text-[11px] text-slate-500 font-mono mt-0.5">
              Evidence Exhibits: <strong className="text-slate-800">{graphData?.total_nodes ?? 0}</strong> • Relational Links: <strong className="text-slate-800">{graphData?.total_edges ?? 0}</strong>
            </div>
          </div>
        </div>

        {/* Compact Case Selector & Seed */}
        <div className="flex items-center gap-2 shrink-0">
          <div className="flex items-center gap-1.5 text-xs font-mono text-slate-600">
            <span>Case:</span>
            <select
              value={selectedCaseId}
              onChange={e => handleCaseChange(e.target.value)}
              className="ws-select text-xs font-mono !py-1 bg-white border-slate-200 text-slate-800"
            >
              {cases.map(c => (
                <option key={c._id} value={c._id}>
                  {c.case_number} - {c.title}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={handleSeedDemo}
            disabled={seeding}
            className="ws-btn ws-btn-secondary !py-1 !text-xs"
            title="Seed sample forensic case with real evidence"
          >
            <Database className="w-3.5 h-3.5 text-indigo-600" />
            <span>{seeding ? 'Seeding...' : 'Seed Data'}</span>
          </button>
        </div>
      </div>

      {/* 2. GRAPH TOOLBAR */}
      <div className="ws-panel p-2.5 flex flex-wrap items-center justify-between gap-3 text-xs bg-white border border-slate-200 shadow-xs">
        {/* Search & Filters */}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
            <input
              type="text"
              placeholder="Search entities, IDs, hashes..."
              value={graphSearch}
              onChange={e => setGraphSearch(e.target.value)}
              className="ws-input pl-8 w-56 text-xs bg-white border-slate-200 text-slate-800"
            />
          </div>

          <select
            value={graphFilterType}
            onChange={e => setGraphFilterType(e.target.value)}
            className="ws-select text-xs bg-white border-slate-200 text-slate-800"
          >
            <option value="ALL">All Entity Types ({graphData?.total_nodes ?? 0})</option>
            <option value="EVIDENCE">Evidence Files</option>
            <option value="BACKUP">Vault Backups</option>
            <option value="EVENT">Timeline Events</option>
            <option value="DEVICE">Hardware Terminals</option>
            <option value="INVESTIGATOR">Investigators</option>
            <option value="LOCATION">Incident Locations</option>
          </select>

          {/* Custody Visibility Toggle */}
          <button
            onClick={() => setShowCustodyNodes(!showCustodyNodes)}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-mono font-medium border transition-colors cursor-pointer flex items-center gap-1.5 ${
              showCustodyNodes
                ? 'bg-blue-50 text-blue-700 border-blue-200 font-semibold'
                : 'bg-slate-100 text-slate-500 border-slate-200'
            }`}
            title="Toggle Chain of Custody nodes visibility in the graph"
          >
            <span>Custody Nodes:</span>
            <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${showCustodyNodes ? 'bg-blue-600 text-white' : 'bg-slate-300 text-slate-700'}`}>
              {showCustodyNodes ? 'Visible' : 'Hidden'}
            </span>
          </button>

          {/* Layout Switchers */}
          <div className="flex items-center rounded-lg border border-slate-200 bg-slate-50 p-0.5 font-mono text-[11px]">
            <button
              onClick={() => setLayoutMode('TREE')}
              className={`px-2.5 py-1 rounded transition-colors cursor-pointer ${
                layoutMode === 'TREE'
                  ? 'bg-white text-blue-600 font-bold shadow-2xs border border-slate-200'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Hierarchy
            </button>
            <button
              onClick={() => setLayoutMode('LAYERED')}
              className={`px-2.5 py-1 rounded transition-colors cursor-pointer ${
                layoutMode === 'LAYERED'
                  ? 'bg-white text-blue-600 font-bold shadow-2xs border border-slate-200'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Pipeline
            </button>
            <button
              onClick={() => setLayoutMode('FORCE')}
              className={`px-2.5 py-1 rounded transition-colors cursor-pointer ${
                layoutMode === 'FORCE'
                  ? 'bg-white text-blue-600 font-bold shadow-2xs border border-slate-200'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Organic
            </button>
          </div>
        </div>

        {/* Camera & Navigation Controls */}
        <div className="flex items-center gap-2">
          <div className="flex items-center rounded-lg border border-slate-200 bg-white overflow-hidden text-xs shadow-2xs">
            <button
              onClick={() => setGraphZoom(z => Math.max(0.3, Number((z - 0.15).toFixed(2))))}
              className="p-1.5 hover:bg-slate-100 text-slate-600 hover:text-slate-900 cursor-pointer"
              title="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="px-2 font-mono text-[11px] text-slate-700 min-w-[44px] text-center font-bold">
              {Math.round(graphZoom * 100)}%
            </span>
            <button
              onClick={() => setGraphZoom(z => Math.min(2.5, Number((z + 0.15).toFixed(2))))}
              className="p-1.5 hover:bg-slate-100 text-slate-600 hover:text-slate-900 cursor-pointer"
              title="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={fitToView}
              className="p-1.5 border-l border-slate-200 hover:bg-slate-100 text-blue-600 cursor-pointer"
              title="Fit & Center View"
            >
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
          </div>

          <button
            onClick={loadGraph}
            className="ws-btn ws-btn-secondary !p-1.5 cursor-pointer"
            title="Reload Topology"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-blue-600 ${graphLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* 3. MAIN WORKSPACE: GRAPH CANVAS + FORENSIC INSPECTOR */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Graph Canvas Viewport */}
        <div className="lg:col-span-8 xl:col-span-9 ws-panel overflow-hidden flex flex-col h-[650px] relative bg-white border border-slate-200 shadow-xs">
          <div className="flex-1 relative cursor-crosshair overflow-hidden bg-white">
            <canvas
              ref={canvasRef}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              onWheel={handleWheel}
              className="w-full h-full block"
            />

            {/* Empty State Banner */}
            {(!graphData || graphData.nodes.length === 0) && !graphLoading && (
              <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center bg-white/95 space-y-3">
                <Network className="w-10 h-10 text-slate-400" />
                <p className="text-sm font-bold text-slate-800">No Entities In Selected Case</p>
                <p className="text-xs text-slate-500 max-w-sm">
                  Upload exhibits or record timeline events to generate the relational topology.
                </p>
                <button
                  onClick={handleSeedDemo}
                  disabled={seeding}
                  className="ws-btn ws-btn-amber mt-2"
                >
                  {seeding ? 'Generating...' : 'Seed Sample Investigation'}
                </button>
              </div>
            )}
          </div>

          {/* Canvas Bottom Legend */}
          <div className="p-2.5 bg-slate-50 border-t border-slate-200 flex flex-wrap items-center justify-between gap-3 text-[11px] font-mono text-slate-600">
            <div className="flex items-center gap-3.5 flex-wrap">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded bg-blue-600"></span>
                <span className="text-slate-700 font-medium">Case Root</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded bg-sky-600"></span>
                <span className="text-slate-700 font-medium">Evidence File</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded bg-amber-600"></span>
                <span className="text-slate-700 font-medium">Vault Backup</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded bg-red-600"></span>
                <span className="text-slate-700 font-medium">Threat / Tampered</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded bg-emerald-600"></span>
                <span className="text-slate-700 font-medium">Investigator</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded bg-indigo-600"></span>
                <span className="text-slate-700 font-medium">Terminal Node</span>
              </span>
            </div>
            <span className="text-slate-500">Scroll to zoom • Drag nodes to organize • Click to inspect record</span>
          </div>
        </div>

        {/* Right Forensic Evidence Record Inspector */}
        <div className="lg:col-span-4 xl:col-span-3 ws-panel p-4 flex flex-col justify-between h-[650px] overflow-y-auto bg-white border border-slate-200 shadow-xs">
          <div className="space-y-4">
            {/* Inspector Header */}
            <div className="flex items-center justify-between border-b border-slate-200 pb-2.5">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-blue-600" />
                <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider font-mono">
                  Evidence Inspector
                </h3>
              </div>
              {selectedNode && (
                <span className="ws-badge ws-badge-blue">
                  {selectedNode.node_type}
                </span>
              )}
            </div>

            {selectedNode ? (
              <div className="space-y-3.5 text-xs">
                {/* Entity Label */}
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider block font-mono">
                    Entity Label
                  </span>
                  <div className="text-sm font-bold text-slate-900 mt-0.5 break-words">
                    {selectedNode.label}
                  </div>
                </div>

                {/* Structured Metadata Properties */}
                <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-2 font-mono text-[11px]">
                  <div className="flex justify-between py-0.5 border-b border-slate-200">
                    <span className="text-slate-500">ID:</span>
                    <span className="text-slate-700 truncate max-w-[150px] font-bold">{selectedNode.id}</span>
                  </div>

                  <div className="flex justify-between py-0.5 border-b border-slate-200">
                    <span className="text-slate-500">TYPE:</span>
                    <span className="text-slate-900 font-semibold">{selectedNode.node_type}</span>
                  </div>

                  {selectedNode.metadata?.integrity_status && (
                    <div className="flex justify-between items-center py-0.5 border-b border-slate-200">
                      <span className="text-slate-500">INTEGRITY:</span>
                      <span className={`ws-badge ${
                        selectedNode.metadata.integrity_status === 'VERIFIED' ? 'ws-badge-green' : 'ws-badge-red'
                      }`}>
                        {selectedNode.metadata.integrity_status}
                      </span>
                    </div>
                  )}

                  {selectedNode.metadata?.severity && (
                    <div className="flex justify-between items-center py-0.5 border-b border-slate-200">
                      <span className="text-slate-500">SEVERITY:</span>
                      <span className={`ws-badge ${
                        selectedNode.metadata.severity === 'CRITICAL' ? 'ws-badge-red' :
                        selectedNode.metadata.severity === 'HIGH' ? 'ws-badge-amber' : 'ws-badge-blue'
                      }`}>
                        {selectedNode.metadata.severity}
                      </span>
                    </div>
                  )}

                  {selectedNode.metadata?.file_size && (
                    <div className="flex justify-between py-0.5 border-b border-slate-200">
                      <span className="text-slate-500">FILE SIZE:</span>
                      <span className="text-slate-700">{(selectedNode.metadata.file_size / 1024).toFixed(1)} KB</span>
                    </div>
                  )}

                  {selectedNode.metadata?.source_device && (
                    <div className="flex justify-between py-0.5 border-b border-slate-200">
                      <span className="text-slate-500">SOURCE:</span>
                      <span className="text-blue-600 font-semibold">{selectedNode.metadata.source_device}</span>
                    </div>
                  )}
                </div>

                {/* Monospace SHA-256 Hash Display with Copy */}
                {selectedNode.metadata?.sha256_hash && (
                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-[10px] font-mono text-slate-500">
                      <span>SHA-256 CRYPTOGRAPHIC DIGEST</span>
                      <button
                        onClick={() => handleCopyHash(selectedNode.metadata?.sha256_hash)}
                        className="text-blue-600 hover:underline flex items-center gap-1 cursor-pointer font-bold"
                      >
                        {copiedHash ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                        <span>{copiedHash ? 'Copied' : 'Copy'}</span>
                      </button>
                    </div>
                    <div className="p-2 rounded bg-slate-50 border border-slate-200 font-mono text-[10px] text-blue-700 break-all select-all font-semibold">
                      {selectedNode.metadata.sha256_hash}
                    </div>
                  </div>
                )}

                {/* Connected Relationships Ledger */}
                <div className="space-y-1.5">
                  <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider block font-mono">
                    Connected Relationships ({selectedConnections.incoming.length + selectedConnections.outgoing.length})
                  </span>

                  <div className="space-y-1 max-h-36 overflow-y-auto pr-1">
                    {selectedConnections.outgoing.map(({ edge, targetNode }, idx) => (
                      <div
                        key={`out-${idx}`}
                        className="p-1.5 rounded bg-slate-50 border border-slate-200 flex items-center justify-between text-[11px] font-mono"
                      >
                        <span className="text-amber-700 font-semibold">{edge.label || edge.edge_type}</span>
                        <ChevronRight className="w-3 h-3 text-slate-400" />
                        <span className="text-slate-800 truncate max-w-[110px]" title={targetNode?.label}>
                          {targetNode?.label || edge.target}
                        </span>
                      </div>
                    ))}

                    {selectedConnections.incoming.map(({ edge, sourceNode }, idx) => (
                      <div
                        key={`in-${idx}`}
                        className="p-1.5 rounded bg-slate-50 border border-slate-200 flex items-center justify-between text-[11px] font-mono"
                      >
                        <span className="text-slate-800 truncate max-w-[110px]" title={sourceNode?.label}>
                          {sourceNode?.label || edge.source}
                        </span>
                        <ChevronRight className="w-3 h-3 text-slate-400" />
                        <span className="text-sky-700 font-semibold">{edge.label || edge.edge_type}</span>
                      </div>
                    ))}

                    {selectedConnections.incoming.length === 0 && selectedConnections.outgoing.length === 0 && (
                      <div className="text-[11px] text-slate-400 italic py-1">No direct relationships recorded.</div>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              /* Empty State (Useful Case Metrics) */
              <div className="space-y-4 text-xs font-mono">
                <div className="text-center py-6 text-slate-500 space-y-1.5 border-b border-slate-200">
                  <Network className="w-8 h-8 mx-auto text-slate-300" />
                  <p className="font-semibold text-slate-700">Select an entity on the canvas</p>
                  <p className="text-[11px] text-slate-500">Inspect properties, cryptographic hashes, and custody links.</p>
                </div>

                <div className="space-y-2 text-[11px]">
                  <div className="flex justify-between py-1 border-b border-slate-200">
                    <span className="text-slate-500">Total Entities:</span>
                    <span className="text-slate-900 font-bold">{graphData?.total_nodes ?? 0}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-200">
                    <span className="text-slate-500">Evidence Files:</span>
                    <span className="text-sky-700 font-bold">
                      {graphData?.nodes.filter(n => ['EVIDENCE', 'FILE'].includes(String(n.node_type))).length ?? 0}
                    </span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-200">
                    <span className="text-slate-500">Preserved Backups:</span>
                    <span className="text-amber-700 font-bold">
                      {graphData?.nodes.filter(n => String(n.node_type) === 'BACKUP').length ?? 0}
                    </span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-200">
                    <span className="text-slate-500">Threat Incidents:</span>
                    <span className="text-red-700 font-bold">
                      {graphData?.nodes.filter(n => ['EVENT', 'SECURITY_ALERT', 'THREAT_ACTOR'].includes(String(n.node_type))).length ?? 0}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Action Button */}
          {selectedCaseId && (
            <Link
              to={`/cases/${selectedCaseId}`}
              className="ws-btn ws-btn-secondary w-full justify-center mt-3 !py-2 cursor-pointer font-semibold"
            >
              <span>Open Case Dossier</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </Link>
          )}
        </div>
      </div>
    </div>
  );
};

export default EvidenceGraphPage;
