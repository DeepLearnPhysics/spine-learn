#!/usr/bin/env bash
# Read-only. Never print kubeconfig credentials, Secret objects, or pod logs.
set -u
ctx=neutrino-ml
kubectl config current-context
k=(kubectl --context "$ctx" --request-timeout=15s)
"${k[@]}" get namespaces || exit 1
"${k[@]}" version -o yaml
"${k[@]}" auth can-i --list
"${k[@]}" get deployments,statefulsets,services -A
"${k[@]}" get applications.argoproj.io,appprojects.argoproj.io -A
"${k[@]}" get crds -o custom-columns=NAME:.metadata.name
"${k[@]}" get resourcequotas,limitranges -A
"${k[@]}" top pods -A
"${k[@]}" get nodes -o custom-columns=NAME:.metadata.name,CPU:.status.allocatable.cpu,MEMORY:.status.allocatable.memory
"${k[@]}" -n spine-learn get deployment spine-learn -o 'jsonpath={.spec.template.spec.containers[*].image}{"\n"}'
"${k[@]}" -n spine-learn get pods,services,httproutes
"${k[@]}" -n spine-learn get httproute spine-learn -o 'jsonpath={.spec.parentRefs}{"\n"}{.status.parents}{"\n"}'
for resource in namespaces customresourcedefinitions.apiextensions.k8s.io; do
  "${k[@]}" auth can-i create "$resource"
done
for namespace in argocd spine-learn; do
  for resource in roles rolebindings deployments services secrets; do
    "${k[@]}" auth can-i create "$resource" -n "$namespace"
  done
done
