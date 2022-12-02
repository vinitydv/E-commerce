from django.shortcuts import render
from django.http import HttpResponse
from .models import product,Contact,Orders,OrderUpdate
from math import ceil
import json
from paytm import Checksum
from django.views.decorators.csrf import csrf_exempt
# Create your views here.


MERCHANT_KEY = 'your merchant-key';
def index(request):
    # products=product.objects.all()
    # print(products)
    allprods=[]
    catprods=product.objects.values('category','id')
    cats={item["category"] for item in catprods}
    for cat in cats:
        prod=product.objects.filter(category=cat)
        n=len(prod)
        nslides=n//4+ceil((n/4)-(n//4))
        # allprods=[[products,range(1,nslides),nslides],[products,range(1,nslides),nslides]]
        # params={'no_of_slides':nslides,'range':range(1,nslides),'product':products}
        allprods.append([prod,range(1,nslides),nslides])
    params={'allprods':allprods}
    return render(request,'shop/index.html',params)

def searchMatch(query,item):
    if query in item.product_name.lower() or query in item.category.lower():
        return True
    else:
        return False


def search(request):
    query=request.GET.get('search')
    allprods=[]
    catprods=product.objects.values('category','id')
    cats={item["category"] for item in catprods}
    for cat in cats:
        prodtemp=product.objects.filter(category=cat)
        prod=[item for item in prodtemp if searchMatch(query,item)]
        n=len(prod)
        nslides=n//4+ceil((n/4)-(n//4))
        if len(prod)!=0:
        # allprods=[[products,range(1,nslides),nslides],[products,range(1,nslides),nslides]]
        # params={'no_of_slides':nslides,'range':range(1,nslides),'product':products}
            allprods.append([prod,range(1,nslides),nslides])
            
    params={'allprods':allprods,'msg':""}
    if len(allprods)==0 or len(query)<4:
        params={'msg':"please make sure to enter relevant search query"}
    return render(request,'shop/search.html',params)


def about(request):
    return render(request,'shop/about.html')


def contact(request):
    thank=False
    if request.method=="POST":
        print(request)
        name=request.POST.get('name','')
        email=request.POST.get('email','')
        phone=request.POST.get('phone','')
        desc=request.POST.get('desc','')
        # print(name,email,phone,desc)
        contact = Contact(name=name, email=email, phone=phone, desc=desc)
        contact.save()
        thank=True 
    return render(request,'shop/contact.html',{'thank':thank})


def tracker(request):
    if request.method=="POST":
        orderId=request.POST.get('orderId','')
        email=request.POST.get('email','')
        try:
            order=Orders.objects.filter(order_id=orderId,email=email)
            if len(order)>0:
                update=OrderUpdate.objects.filter(order_id=orderId)
                updates=[]
                for item in update:
                    updates.append({'text':item.update_desc,'time':item.timestamp})
                    response=json.dumps({"status":"success","updates":updates,"itemsJson":order[0].items_json},default=str)
                return HttpResponse(response)
            else:
                return HttpResponse('{"status":"noitem"}')
        except Exception as e:
            return HttpResponse('{"status":"error"}')
    return render(request,'shop/tracker.html')


def productview(request,myid):
    produc=product.objects.filter(id=myid)
    # print(produc)
    return render(request,'shop/productview.html',{'product':produc[0]})


def checkout(request):
    if request.method=="POST":
        items_json=request.POST.get('itemsJson','')
        name=request.POST.get('name','')
        email=request.POST.get('email','')
        amount=request.POST.get('amount','')
        address=request.POST.get('address1','')+""+request.POST.get('adress2','')
        city=request.POST.get('city','')
        state=request.POST.get('state','')
        zip_code=request.POST.get('zip_code','')
        phone=request.POST.get('phone','')
        order=Orders(items_json=items_json,name=name,email=email,address=address,city=city,state=state,zip_code=zip_code,phone=phone,amount=amount)
        order.save()
        update=OrderUpdate(order_id=order.order_id,update_desc="The order has been placed")
        update.save()
        thank=True
        id=order.order_id
        # return render(request,'shop/checkout.html',{'thank':thank,'id':id})
        # Request paytm to transferthe amount to your account after payment by user.
        param_dict={
            'MID':'#your merchant-id',
            'ORDER_ID':str(order.order_id),
            'TXN_AMOUNT':str(amount),
            'CUST_ID':email,
            'INDUSTRY_TYPE_ID':'Retail',
            'WEBSITE':'WEBSTAGING',
            'CHANNEL_ID':'WEB',
            'CALLBACK_URL':'http://127.0.0.1:8000/shop/handlerequest/',
        }
        param_dict['CHECKSUMHASH']=Checksum.generate_checksum(param_dict,MERCHANT_KEY)
        return render(request,'shop/paytm.html',{'param_dict':param_dict})
    return render(request,'shop/checkout.html')

@csrf_exempt
def handlerequest(request):
    # Paytm will send you post request here
    form = request.POST
    response_dict = {}
    for i in form.keys():
        response_dict[i] = form[i]
        if i == 'CHECKSUMHASH':
            checksum = form[i]

    verify = Checksum.verify_checksum(response_dict, MERCHANT_KEY, checksum)
    if verify:
        if response_dict['RESPCODE'] == '01':
            print('order successful')
        else:
            print('order was not successful because' + response_dict['RESPMSG'])
    return render(request, 'shop/paymentstatus.html', {'response': response_dict})
