#api文档参考 https://docs.kubecost.com/apis/monitoring-apis/api-allocation

# 查看某个namespace的24h费用
curl 'http://k8s-kubecost-ingressf-64740fab3c-1395131682.us-west-2.elb.amazonaws.com/model/allocation?window=24h&aggregate=namespace&filter=namespace:"tenant1"&accumulate=true' | jq

# 按照namespace分组查看24h费用
curl 'http://k8s-kubecost-ingressf-64740fab3c-1395131682.us-west-2.elb.amazonaws.com/model/allocation?window=24h&aggregate=namespace&accumulate=true' | jq